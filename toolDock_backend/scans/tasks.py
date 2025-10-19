from celery import shared_task
from django.utils import timezone
from .models import ScanJob, Tool
import time 

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
    job.save()

    # Get the tool runner
    from .utils import get_tool_runner
    try:
        runner = get_tool_runner(job.tool.name)
    except ValueError as e:
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.save()
        raise e

    # Simulate or implement the actual scanning logic with progress updates
    # Assuming the runner has a method like 'run' that takes target, options, and a callback for progress
    # If not, you'll need to wrap the runner logic to update progress periodically

    total_steps = 100  # Example; adjust based on tool
    job.progress = 0
    job.current_step = 'Initializing'
    job.save()

    def progress_callback(current, total, step_description):
        # Callback to update progress
        job.progress = int((current / total) * 100)
        job.current_step = step_description
        job.save()
        # Optionally, update Celery task state if needed for other monitoring
        self.update_state(state='PROGRESS', meta={'progress': job.progress, 'current_step': job.current_step})

    try:
        # If your runner supports progress callback, pass it
        # Example: result = runner.run(job.target, job.options, progress_callback=progress_callback)
        
        # For demonstration (simulate with loop if runner doesn't support)
        for step in range(total_steps):
            time.sleep(0.02)  # Simulate work
            progress_callback(step + 1, total_steps, f"Scanning ports - Step {step + 1}/{total_steps}")
        
        # After completion
        job.raw_output = "Scan results here"  # Set from runner output
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()
        
        # Optionally, create Findings from output
        # Example: Finding.objects.create(job=job, title="Sample finding", ...)

        return {'status': 'completed', 'job_id': str(job.job_id)}

    except Exception as e:
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.save()
        raise e