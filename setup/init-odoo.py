import paramiko
import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("51.77.216.79", username="root", password="thoughtpolice", timeout=10)

cmd = """
CONTROL_PLANE_IP="10.10.10.10"

echo "=== Port-forwarding Odoo ==="
iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 443 -j DNAT --to-destination ${CONTROL_PLANE_IP}:443 2>/dev/null || iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 443 -j DNAT --to-destination ${CONTROL_PLANE_IP}:443
echo "[OK] 443 -> ${CONTROL_PLANE_IP}:443"

iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to-destination ${CONTROL_PLANE_IP}:80 2>/dev/null || iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to-destination ${CONTROL_PLANE_IP}:80
echo "[OK] 80 -> ${CONTROL_PLANE_IP}:80"

iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 6443 -j DNAT --to-destination ${CONTROL_PLANE_IP}:6443 2>/dev/null || iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 6443 -j DNAT --to-destination ${CONTROL_PLANE_IP}:6443
echo "[OK] 6443 -> ${CONTROL_PLANE_IP}:6443"

DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent > /dev/null 2>&1
netfilter-persistent save > /dev/null 2>&1

echo ""
echo "=== Port-forwarding actif ==="
"""

stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
print(stdout.read().decode("utf-8", errors="replace"), end="")
ssh.close()
