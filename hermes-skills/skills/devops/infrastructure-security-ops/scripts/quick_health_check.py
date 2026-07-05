import subprocess
import json
import re
from datetime import datetime

def get_report():
    # Tailscale Check
    status = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True).stdout
    data = json.loads(status)
    
    report = f"📊 **Daily Report - {datetime.now().strftime('%Y-%m-%d')}**\n"
    report += f"Tailnet: {data.get('CurrentTailnet', {}).get('Name')}\n"
    report += f"Address: {data.get('Self', {}).get('TailscaleIPs', ['N/A'])[0]}\n"
    
    # Docker Check
    docker_ps = subprocess.run(["docker", "ps", "--format", "{{.Names}}: {{.Status}}"], capture_output=True, text=True).stdout
    report += "\n🐳 **Containers**\n" + (docker_ps if docker_ps else "None running")
    
    return report

if __name__ == "__main__":
    print(get_report())
