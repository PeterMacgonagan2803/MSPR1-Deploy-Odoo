#!/usr/bin/env python3
"""Diagnostic complet VM 203 : cloud-init, réseau, puis force apply netplan."""
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

# --- Diagnostic via qm guest exec (qemu-agent) ---
# D'abord, essai SSH directement via consoles execute qm monitor
cmds = [
    ("qm monitor 203 'info network' 2>&1 | head -20", "qm monitor réseau 203"),
    ("qm guest exec 203 -- sh -c 'ip addr show; ip route show' 2>&1", "ip addr/route via qemu-agent"),
    ("cat /var/lib/vz/snippets/*.cfg 2>/dev/null || true; "
     "ls -la /var/lib/vz/template/iso/ | grep cloud || true; "
     "qm cloudinit dump 203 network 2>&1", "cloud-init network dump VM 203"),
    ("qm cloudinit dump 203 user 2>&1 | head -30", "cloud-init user dump VM 203"),
]
for cmd, label in cmds:
    print(f"\n=== {label} ===", flush=True)
    _,o,e = s.exec_command(cmd, timeout=30)
    out = (o.read() + e.read()).decode("utf-8","replace").strip()
    print(out[:2000] if out else "(vide)", flush=True)

# Si cloud-init réseau manque, l'injecter via qm set et forcer un reboot
print("\n=== Check cloud-init network via qm cloudinit ===", flush=True)
_,o,_ = s.exec_command("qm cloudinit dump 203 network 2>&1", timeout=20)
net_dump = o.read().decode("utf-8","replace")
print(net_dump[:500], flush=True)

if "10.10.10.13" not in net_dump:
    print("\n PROBLEME: cloud-init réseau n'a pas l'IP 10.10.10.13 !", flush=True)
    print("Force qm set + cloud-init update...", flush=True)
    fix_cmds = [
        "qm set 203 --ipconfig0 ip=10.10.10.13/24,gw=10.10.10.1 2>&1",
        "qm cloudinit update 203 2>&1",
        "qm stop 203 --timeout 10 --skiplock 2>&1; true",
        "sleep 3",
        "qm start 203 2>&1",
    ]
    for cmd in fix_cmds:
        _,o,_ = s.exec_command(cmd, timeout=30)
        print(f"  > {cmd[:60]}: {o.read().decode('utf-8','replace').strip()[:200]}", flush=True)
else:
    print("IP 10.10.10.13 trouvee dans cloud-init. Probleme de boot uniquement.", flush=True)
    print("Force reboot 203...", flush=True)
    s.exec_command("qm reboot 203 2>&1", timeout=10)

# Attente et sonde
print("\nAttente 90s et sonde SSH...", flush=True)
time.sleep(90)
_,o,_ = s.exec_command(
    "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
    "-i /root/.ssh/id_ansible ubuntu@10.10.10.13 'echo SSH_OK; hostname; ip addr show ens18 | grep inet' 2>&1",
    timeout=25
)
out = o.read().decode("utf-8","replace").strip()
print(f"SSH 10.10.10.13: {out}", flush=True)

_,o,_ = s.exec_command("qm list", timeout=15)
print("\n", o.read().decode("utf-8","replace"))
s.close()
