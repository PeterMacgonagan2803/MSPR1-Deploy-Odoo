#!/usr/bin/env python3
"""Lit les logs Packer sur Proxmox en direct."""
import logging, os, sys, time
import paramiko

logging.getLogger("paramiko").setLevel(logging.CRITICAL)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = os.environ.get("MSPR_PROXMOX_HOST", "51.77.216.79")
PASS = os.environ.get("MSPR_PROXMOX_PASS", "thoughtpolice")

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username="root", password=PASS, timeout=25)

_, o, _ = s.exec_command(
    "tail -n 40 /tmp/packer-tee-mspr-deploy.log 2>/dev/null || echo '(log vide)'; "
    "echo '---QM---'; qm list",
    timeout=30
)
print(o.read().decode("utf-8", "replace"))
s.close()
