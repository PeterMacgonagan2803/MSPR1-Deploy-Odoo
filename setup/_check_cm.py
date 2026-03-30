import paramiko, sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.77.216.79", username="root", password="thoughtpolice", timeout=10)
cmd = """ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_ansible ubuntu@10.10.10.10 bash << 'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo "=== cert-manager pods ==="
kubectl get pods -n cert-manager -o wide 2>/dev/null
echo ""
echo "=== Events recents ==="
kubectl get events -n cert-manager --sort-by=.lastTimestamp 2>/dev/null | tail -15
echo ""
echo "=== Helm status ==="
helm status cert-manager -n cert-manager 2>/dev/null | head -10
REMOTE
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
print(stdout.read().decode("utf-8", errors="replace"))
ssh.close()
