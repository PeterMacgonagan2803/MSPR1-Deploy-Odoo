#!/usr/bin/env python3
"""Force reset VM 203 (nfs-server) bloquée au boot, puis sonde SSH."""
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
print("Connecte Proxmox.", flush=True)

# Force stop + start VM 203
for cmd, label in [
    ("qm stop 203 --timeout 5 --skiplock 2>&1; true",    "stop force 203"),
    ("sleep 3",                                           "pause"),
    ("qm start 203 2>&1",                                 "start 203"),
]:
    _,o,_ = s.exec_command(cmd, timeout=60)
    out = o.read().decode("utf-8","replace").strip()
    print(f"[{label}] {out or 'ok'}", flush=True)

# Sonde SSH 10.10.10.13 via bastion sur 3 min max
print("Sonde SSH 10.10.10.13 (nfs-server) via bastion (max 3 min)...", flush=True)
for i in range(18):
    time.sleep(10)
    _,o,_ = s.exec_command(
        "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
        "-i /root/.ssh/id_ansible ubuntu@10.10.10.13 'echo SSH_203_OK' 2>&1", timeout=20
    )
    out = o.read().decode("utf-8","replace").strip()
    print(f"  [{i*10}s] {out}", flush=True)
    if "SSH_203_OK" in out:
        print("VM 203 OK !", flush=True)
        break
else:
    print("TIMEOUT: VM 203 pas joignable apres 3 min.", flush=True)

_,o,_ = s.exec_command("qm list", timeout=15)
print("\nqm list:", o.read().decode("utf-8","replace"))
s.close()
