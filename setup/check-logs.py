import paramiko
import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.77.216.79", username="root", password="thoughtpolice", timeout=10)

cmd = """ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_ansible ubuntu@10.10.10.10 '
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo "=== Odoo Logs (last 30 lines) ==="
kubectl logs -n odoo deployment/odoo --tail=30
echo ""
echo "=== PostgreSQL Logs (last 10 lines) ==="
kubectl logs -n odoo deployment/postgres --tail=10
'"""

stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode("utf-8", errors="replace"), end="")
ssh.close()
