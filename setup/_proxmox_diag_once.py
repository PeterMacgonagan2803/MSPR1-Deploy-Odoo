#!/usr/bin/env python3
"""Diagnostic rapide via SSH root@Proxmox."""
import paramiko

HOST = "51.77.216.79"
USER = "root"
PASS = "thoughtpolice"

CMDS = [
    "echo '=== qm list (9002) ===' && qm list | grep -E '^(VMID|9002)' || qm list | head -15",
    "echo '=== ping 10.10.10.99 ===' && ping -c 2 -W 2 10.10.10.99 2>&1 || true",
    "echo '=== ssh test from Proxmox (sshpass) ===' && "
    "(command -v sshpass >/dev/null && sshpass -p ubuntu ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
    "-o ConnectTimeout=10 -o PreferredAuthentications=password -o PubkeyAuthentication=no ubuntu@10.10.10.99 'hostname; whoami' 2>&1) "
    "|| echo 'sshpass_absent_or_ssh_failed'",
]

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=25)
    print("Connecte Proxmox OK\n")
    for cmd in CMDS:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=45)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        print(out)
        if err.strip():
            print("STDERR:", err[:600])
    ssh.close()

if __name__ == "__main__":
    main()
