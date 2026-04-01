#!/usr/bin/env python3
"""Lance packer build sur Proxmox avec logs complets (timeout 60 min)."""
import os
import paramiko
import sys

HOST = os.environ.get("MSPR_PROXMOX_HOST", "51.77.216.79")
USER = os.environ.get("MSPR_PROXMOX_USER", "root")
PASS = os.environ.get("MSPR_PROXMOX_PASS", "thoughtpolice")
VM_ID = "9002"

CMD = f"""
set -e
cd /root/MSPR1-Deploy-Odoo
git fetch origin && git reset --hard origin/main
HASH=$(openssl passwd -6 ubuntu)
sed -i "s|__UBUNTU_HASH__|${{HASH}}|" packer/http/user-data
echo "=== user-data (debut) ==="
head -35 packer/http/user-data

qm stop {VM_ID} --timeout 20 2>/dev/null || true
sleep 2
qm destroy {VM_ID} --purge 2>/dev/null || true

cd packer
packer init .

export PACKER_LOG=1
export PACKER_LOG_PATH=/tmp/packer-last.log
rm -f /tmp/packer-tee.log

packer build \\
  -var 'proxmox_password={PASS}' \\
  -var 'proxmox_node=ns3139245' \\
  -var 'vm_id={VM_ID}' \\
  . 2>&1 | tee /tmp/packer-tee.log

echo "=== qm list ==="
qm list | grep {VM_ID} || true
echo DONE
"""


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    print("Connexion OK, packer build demarre (jusqua 60 min)...", flush=True)
    stdin, stdout, stderr = ssh.exec_command(CMD, timeout=3600)
    for line in iter(stdout.readline, ""):
        sys.stdout.write(line)
        sys.stdout.flush()
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    ssh.close()
    if err:
        print("STDERR:", err[:2000], flush=True)
    print(f"Exit code: {code}", flush=True)
    sys.exit(code)


if __name__ == "__main__":
    main()
