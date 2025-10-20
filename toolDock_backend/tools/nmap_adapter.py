import subprocess
from urllib.parse import urlparse
import re
from typing import Callable, Optional

class NmapRunner:
    def run(self, target: str, options: dict, progress_callback: Optional[Callable[[int, str], None]] = None) -> str:
        """
        Run nmap scan on the target with given options.
        
        :param target: The target IP or hostname to scan.
        :param options: Dictionary of options, e.g., {"scan_type": "quick", "ports": "1-1000"}.
        :param progress_callback: Optional callback function to report progress.
                                  Takes two args: progress_percent (int 0-100), step_description (str).
        :return: Raw XML output from nmap.

        """
        parsed = urlparse(target)
        if parsed.scheme in ('http', 'https'):
            target = parsed.netloc  

        scan_type = options.get('scan_type', 'full') or 'full'
        
        # Base nmap command with XML output (-oX -) for easy parsing later
        args = ['nmap', '-oX', '-', '--stats-every', '5s']  # Add stats every 5s for progress updates
        
        # Add verbosity for more output lines to parse
        args += ['-v']
        
        # Customize based on scan_type
        if scan_type == 'quick':
            args += ['-T4', '--top-ports', '100']  # Aggressive timing, top 100 ports for quick scan
        else:
            args += ['-sV', '-O']  # Version detection, OS detection for full scan
        
        # Add custom ports if specified
        if 'ports' in options:
            args += ['-p', options['ports']]
        
        # Add target last
        args.append(target)
        
        # Start subprocess with piped stdout/stderr
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        output = ''  # Accumulate XML output
        phase = 'Initializing'  # Track current phase
        progress = 0  # Estimated progress 0-100
        
        # Regex patterns to detect progress (adjust based on nmap output)
        stats_pattern = re.compile(r'Syn Scan Timing: About (\d+\.\d+)% done')  # Example: "About 50.00% done"
        completion_pattern = re.compile(r'Nmap scan report for')  # When starting host reports
        phase_patterns = {
            'Host discovery': re.compile(r'Host discovery performed'),
            'Port scanning': re.compile(r'SYN Stealth Scan'),
            'Service detection': re.compile(r'Service scan Timing'),
            'OS detection': re.compile(r'OS detection performed'),
        }
        
        # Read stdout line by line for real-time progress
        while True:
            line = process.stdout.readline() # type: ignore
            if not line and process.poll() is not None:
                break  # Process done
            if line:
                output += line
                
                # Parse for progress/stats
                stats_match = stats_pattern.search(line)
                if stats_match:
                    new_progress = int(float(stats_match.group(1)))
                    if new_progress > progress:
                        progress = new_progress
                        if progress_callback:
                            progress_callback(progress, f'{phase} - {progress}% complete')
                
                # Detect phase changes
                for new_phase, pattern in phase_patterns.items():
                    if pattern.search(line):
                        phase = new_phase
                        if progress_callback:
                            progress_callback(progress, f'Entering phase: {phase}')
                
                # On completion indicators
                if 'Nmap done' in line or completion_pattern.search(line):
                    progress = 100
                    if progress_callback:
                        progress_callback(100, 'Scan completed')

        # Wait for process to fully exit and capture any remaining output/err
        stderr = process.stderr.read() # type: ignore
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError(f'nmap failed with code {process.returncode}: {stderr}')
        
        # Callback final if not already
        if progress_callback and progress < 100:
            progress_callback(100, 'Scan completed')
        
        return output  # Raw XML string for parsing into findings