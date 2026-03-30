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
echo "=== Pods ==="
kubectl get pods -n odoo
echo ""
echo "=== Odoo HTTP test ==="
curl -s -o /dev/null -w "  /web -> HTTP %{http_code}\n" http://10.43.83.134:8069/web
curl -s -o /dev/null -w "  /web/database/manager -> HTTP %{http_code}\n" http://10.43.83.134:8069/web/database/manager
echo ""
echo "=== Services ==="
kubectl get svc -n odoo
echo ""
echo "=== Ingress ==="
kubectl get ingress -n odoo
'"""

stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode("utf-8", errors="replace"), end="")
ssh.close()
