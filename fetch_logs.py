import urllib.request
import json
import ssl

try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request('https://api.github.com/repos/ManojKuppala/daily-ai-mentor/actions/runs')
    res = urllib.request.urlopen(req, context=ctx)
    data = json.loads(res.read())
    
    # Get latest run
    latest_run = data['workflow_runs'][0]
    print(f"Latest run ID: {latest_run['id']}, status: {latest_run['conclusion']}")
    
    jobs_url = latest_run['jobs_url']
    req2 = urllib.request.Request(jobs_url)
    res2 = urllib.request.urlopen(req2, context=ctx)
    jobs_data = json.loads(res2.read())
    
    job_id = jobs_data['jobs'][0]['id']
    log_url = f"https://api.github.com/repos/ManojKuppala/daily-ai-mentor/actions/jobs/{job_id}/logs"
    
    print(f"Fetching logs from: {log_url}")
    
    # GitHub redirects log downloads, so we need to handle it or let urllib do it
    req3 = urllib.request.Request(log_url)
    res3 = urllib.request.urlopen(req3, context=ctx)
    logs = res3.read().decode('utf-8')
    
    with open('latest_log.txt', 'w', encoding='utf-8') as f:
        f.write(logs)
    print("Logs saved to latest_log.txt")
except Exception as e:
    print(f"Error: {e}")
