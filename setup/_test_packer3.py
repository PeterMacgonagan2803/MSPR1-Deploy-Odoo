"""Test Packer v3 - CD-ROM autoinstall (pas HTTP)."""
import paramiko
import sys
import time

HOST = "51.77.216.79"
USER = "root"
PASS = "thoughtpolice"

def ssh_run(cmd, timeout=900, label=""):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    print(f"\n--- {label} ---", flush=True)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    ssh.close()
    for line in out.strip().split("\n")[-60:]:
        print(f"  {line}", flush=True)
    if code != 0:
        for line in err.strip().split("\n")[-15:]:
            print(f"  [ERR] {line}", flush=True)
        print(f"  EXIT CODE: {code}", flush=True)
    return out, err, code

# Pull latest
ssh_run(r"""
cd /root/MSPR1-Deploy-Odoo
git pull --ff-only 2>&1 | tail -5

# Regenerate hash in user-data
HASH=$(openssl passwd -6 ubuntu)
sed -i "s|__UBUNTU_HASH__|${HASH}|" packer/http/user-data
echo "user-data:"
cat packer/http/user-data
echo ""
echo "packer config (boot + iso):"
grep -A5 'boot_command\|additional_iso' packer/ubuntu-k3s.pkr.hcl
echo "PREP_OK"
""", label="PULL + PREP")

# Build
print("\n=== PACKER BUILD v3 (CD-ROM) ===", flush=True)
print("~15-20 min autoinstall...", flush=True)
t = time.time()

ssh_run("""
cd /root/MSPR1-Deploy-Odoo/packer

packer init . 2>&1 | tail -5
echo ""
packer build \
    -var "proxmox_password=thoughtpolice" \
    -var "proxmox_node=ns3139245" \
    -var "vm_id=9001" \
    . 2>&1 | tail -100
""", timeout=1800, label="PACKER BUILD v3")

elapsed = int(time.time() - t)
print(f"\nDuree: {elapsed//60}m{elapsed%60:02d}s", flush=True)

# Verify
out, _, _ = ssh_run("""
qm list | grep 9001 && echo "PACKER_SUCCESS" || echo "PACKER_FAIL"
""", label="VERIFY")

if "PACKER_SUCCESS" in out:
    print("\n*** PACKER TEST REUSSI ***", flush=True)
    ssh_run("qm destroy 9001 --purge && echo 'Cleanup OK'", label="CLEANUP")
else:
    print("\n*** PACKER ECHOUE ***", flush=True)
