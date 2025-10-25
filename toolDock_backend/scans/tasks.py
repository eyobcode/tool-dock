import json
from celery import shared_task
from django.utils import timezone
from .models import ScanJob, Finding
import time

# logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_scan_task(self, job_id):
    # Fetch the ScanJob instance
    try:
        job = ScanJob.objects.get(job_id=job_id)
    except ScanJob.DoesNotExist:
        raise ValueError(f"ScanJob with job_id {job_id} does not exist")

    # Update status to 'running' and set started_at
    job.status = 'running'
    job.started_at = timezone.now()
    job.current_step = 'Initializing scan'
    job.save(update_fields=['status', 'started_at', 'current_step'])

    # Get the tool runner
    from .utils import get_tool_runner # type: ignore
    try:
        runner = get_tool_runner(job.tool.name)
    except ValueError as e:
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'completed_at'])
        raise

    enable_progress = job.tool.estimated_duration > 30
    last_update_time = time.time()

    def progress_callback(progress_percent, step_description, force_save=False):
        nonlocal last_update_time
        if not enable_progress and not force_save:
            return  # Skip for quick tools, except forced saves
        current_time = time.time()
        if force_save or (current_time - last_update_time >= 5):  # Throttle to every 5+ seconds
            job.progress = progress_percent
            job.current_step = step_description
            job.save(update_fields=['progress', 'current_step'])
            last_update_time = current_time  # Update timestamp
            # Optional: Celery state for monitoring tools
            self.update_state(state='PROGRESS', meta={'progress': progress_percent, 'current_step': step_description})

    try:
        # Initial progress (0%) right before runner
        progress_callback(0, 'Starting scan', force_save=True)

        opts = job.options

        # Normalize:
        if opts is None or (isinstance(opts, str) and opts.strip() == ""):
            opts = {}
        elif isinstance(opts, str):
            try:
                opts = json.loads(opts)
            except Exception:
                opts = {}
        elif isinstance(opts, dict):
            # already good
            pass
        else:
            # Try to coerce (for example a QueryDict or list of pairs)
            try:
                opts = dict(opts)
            except Exception:
                opts = {}

        # final safe fallback
        opts = opts or {}

        raw_output = runner.run(job.target, opts, progress_callback=progress_callback)


        # Final progress (100%) after runner, force save
        progress_callback(100, 'Scan completed', force_save=True)

        # Save raw_output, status, etc.
        job.raw_output = raw_output
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save(update_fields=['raw_output', 'status', 'completed_at'])

        # parse findings (pure function)
        findings_data = parse_scan_output(raw_output, job.tool.name)
        
        # Create DB findings
        # with transaction.atomic():
        for finding in findings_data:
            Finding.objects.create(
                job=job,
                severity=finding.get('severity', 'info'),
                title=finding.get('title', 'Untitled Finding'),
                description=finding.get('description', ''),
                category=finding.get('category', ''),
                cvss_score=finding.get('cvss_score', 0.0),
                cve_ids=finding.get('cve_ids', []),
                port=finding.get('port'),
                protocol=finding.get('protocol'),
                service=finding.get('service'),
                version=finding.get('version'),
                remediation=finding.get('remediation', ''),
                references=finding.get('references', []),
                affected_component=finding.get('affected_component', '')
            )

        return findings_data

    except Exception as e:
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.current_step = f'Error: {str(e)}'
        job.save(update_fields=['status', 'completed_at', 'current_step'])
        raise


# parsing function (no prints, no file IO)
import xml.etree.ElementTree as ET
from typing import List, Dict

def parse_scan_output(raw_output: str, tool_name: str) -> List[Dict]:
    """
    Parse Nmap XML output and extract findings for the Finding model.
    
    This function assumes the raw_output is Nmap's XML format (from -oX).
    It extracts open ports/services as basic 'info' findings and, if vulners NSE script
    was used, extracts vulnerabilities with CVE, CVSS, etc.
    
    :param raw_output: The raw XML string from Nmap.
    :param tool_name: The tool name (e.g., 'nmap') for filtering/custom logic.
    :return: List of dicts, each representing a Finding object's fields.
    """
    if tool_name != 'nmap':
        return []  # Only handle nmap for this example; extend for other tools
    
    findings = []
    try:
        root = ET.fromstring(raw_output)
    except ET.ParseError as e:
        # Handle invalid XML (e.g., incomplete scan)
        return [{'title': 'Parse Error', 'description': f'Failed to parse Nmap XML: {str(e)}', 'severity': 'critical'}]
    
    # Iterate over each <host> in the <nmaprun>
    for host in root.findall('host'):
        addr_elem = host.find("address[@addrtype='ipv4']")
        host_address = addr_elem.get('addr') if addr_elem is not None else 'Unknown'
        # Extract ports and services
        ports = host.find('ports')
        if ports is None:
            continue

        for port in ports.findall('port'):
            state_elem = port.find('state')
            if state_elem is None or state_elem.get('state') != 'open': # Only open ports
                continue

            port_id = int(port.get('portid')) # type: ignore
            protocol = port.get('protocol', 'tcp')

            service_elem = port.find('service')
            service_name = service_elem.get('name') if service_elem is not None else 'Unknown'
            if service_elem is not None:
                version = ' '.join(filter(None, [
                    service_elem.get('product'),
                    service_elem.get('version')
                ])).strip()
            else:
                version = ''

            finding = {
                'severity': 'info', # Default; override if vuln found
                'title': f'Open Port: {port_id}/{protocol}',
                'description': f'Open port detected on {host_address}. Service: {service_name}. Version: {version}.',
                'category': 'Network Exposure',
                'cvss_score': 0.0,
                'cve_ids': [],
                'port': port_id,
                'protocol': protocol,
                'service': service_name,
                'version': version,
                'remediation': 'Ensure this port is necessary and properly secured (e.g., firewall rules, updates).',
                'references': [],
                'affected_component': host_address
            }

            # Check for script outputs (e.g., vulners for vulnerabilities)
            for script in port.findall('script'):
                if script.get('id') == 'vulners':
                    # Parse vulners output: Typically a <table> with <elem> for cve, cvss, etc.
                    for table in script.findall('table'):
                        cve = ''
                        cvss = 0.0
                        refs = []
                        for elem in table.findall('elem'):
                            key = elem.get('key')
                            if key == 'id':
                                cve = elem.text
                            elif key == 'cvss':
                                try:
                                    cvss = float(elem.text) # type: ignore
                                except (ValueError, TypeError):
                                    cvss = 0.0
                            elif key == 'references':
                                refs = elem.text.split() if elem.text else []  # Assuming space-separated

                        if cve:
                            finding['cve_ids'].append(cve)
                            finding['cvss_score'] = max(finding['cvss_score'], cvss)  # Take highest
                            finding['references'].extend(refs)
                            # Update severity based on CVSS (common mapping)
                            if cvss >= 9.0:
                                finding['severity'] = 'critical'
                            elif cvss >= 7.0:
                                finding['severity'] = 'high'
                            elif cvss >= 4.0:
                                finding['severity'] = 'medium'
                            elif cvss > 0.0:
                                finding['severity'] = 'low'
                            # Enhance description and remediation
                            finding['description'] += f'\nVulnerability: {cve} (CVSS: {cvss}).'
                            finding['remediation'] += ' Apply patches or mitigations as per references.'

            findings.append(finding)

    return findings
