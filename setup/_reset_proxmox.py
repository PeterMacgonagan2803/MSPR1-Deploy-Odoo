#!/usr/bin/env python3
"""Reset Proxmox complet avant deploy-all avec Packer."""
import logging
import os
import sys
import paramiko

logging.getLogger("paramiko").setLevel(logging.CRITICAL)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = os.environ.get("MSPR_PROXMOX_HOST", "51.77.216.79")
USER = os.environ.get("MSPR_PROXMOX_USER", "root")
PASS = os.environ.get("MSPR_PROXMOX_PASS", "thoughtpolice")

print(f"Connexion {USER}@{HOST}...", flush=True)
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username=USER, password=PASS, timeout=25)
print("Connecte.", flush=True)

RESET_CMD = (
    "killall -9 ansible-playbook 2>/dev/null || true; "
    "killall -9 ansible 2>/dev/null || true; "
    "killall -9 packer 2>/dev/null || true; "
    "sleep 2; "
    "for vmid in 200 201 202 203 9000 9002; do "
    "  qm stop $vmid --timeout 15 2>/dev/null || true; sleep 1; "
    "  qm destroy $vmid --purge 2>/dev/null && echo VM_$vmid_OK || echo VM_$vmid_ABSENT; "
    "done; "
    "iptables -t nat -F PREROUTING 2>/dev/null || true; "
    "echo 1 > /proc/sys/net/ipv4/ip_forward; "
    "iptables -t nat -C POSTROUTING -s 10.10.10.0/24 -o vmbr0 -j MASQUERADE 2>/dev/null || "
    "iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o vmbr0 -j MASQUERADE; "
    "rm -rf /root/MSPR1-Deploy-Odoo; "
    "rm -f /root/.ssh/known_hosts; "
    "qm list; "
    "echo RESET_OK"
)

_, o, e = s.exec_command(RESET_CMD, timeout=180)
out = o.read().decode("utf-8", errors="replace")
err = e.read().decode("utf-8", errors="replace")
print(out or "(pas de sortie)")
if err.strip():
    print("STDERR:", err[:800])
s.close()
print("Script termine.", flush=True)
