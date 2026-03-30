import paramiko, sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.77.216.79", username="root", password="thoughtpolice", timeout=10)
cmd = """ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_ansible ubuntu@10.10.10.10 bash << 'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo "=== NODES ==="
kubectl get nodes
echo ""
echo "=== PODS cert-manager ==="
kubectl get pods -n cert-manager -o wide 2>/dev/null || echo "Namespace cert-manager absent"
echo ""
echo "=== Events cert-manager (derniers) ==="
kubectl get events -n cert-manager --sort-by=.lastTimestamp 2>/dev/null | tail -20
echo ""
echo "=== Pod describe (conditions) ==="
for pod in $(kubectl get pods -n cert-manager -o name 2>/dev/null); do
    echo "--- $pod ---"
    kubectl describe $pod -n cert-manager 2>/dev/null | tail -20
done
echo ""
echo "=== Helm releases ==="
helm list -A 2>/dev/null
REMOTE
"""
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
print(stdout.read().decode("utf-8", errors="replace"))
err = stderr.read().decode("utf-8", errors="replace")
if err:
    print("STDERR:", err[:500])
ssh.close()
