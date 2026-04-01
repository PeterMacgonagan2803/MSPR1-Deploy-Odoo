"""Test Packer v6 - HTTP + kernel ip= + user-data simplifie."""
import paramiko
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
    for line in out.strip().split("\n")[-80:]:
        print(f"  {line}", flush=True)
    if code != 0:
        for line in err.strip().split("\n")[-10:]:
            print(f"  [ERR] {line}", flush=True)
    return out, err, code

# Pull + hash
ssh_run(r"""
cd /root/MSPR1-Deploy-Odoo && git pull --ff-only 2>&1 | tail -3
HASH=$(openssl passwd -6 ubuntu)
sed -i "s|__UBUNTU_HASH__|${HASH}|" packer/http/user-data
echo "--- user-data ---"
cat packer/http/user-data
echo "PREP_OK"
""", label="PULL+HASH")

# Cleanup
ssh_run("qm stop 9001 --timeout 10 2>/dev/null; qm destroy 9001 --purge 2>/dev/null; echo OK", label="CLEANUP")

# Build
print("\n=== PACKER BUILD v6 ===", flush=True)
t = time.time()

ssh_run("""
cd /root/MSPR1-Deploy-Odoo/packer
packer init . 2>&1 | tail -3
echo "=== build ==="
packer build \
    -var "proxmox_password=thoughtpolice" \
    -var "proxmox_node=ns3139245" \
    -var "vm_id=9001" \
    . 2>&1 | tail -100
""", timeout=1800, label="BUILD")

elapsed = int(time.time() - t)
print(f"\nDuree: {elapsed//60}m{elapsed%60:02d}s", flush=True)

# Verify
out, _, _ = ssh_run("qm list | grep 9001 && echo PACKER_SUCCESS || echo PACKER_FAIL", label="VERIFY")
if "PACKER_SUCCESS" in out:
    print("\n*** PACKER REUSSI ***", flush=True)
else:
    print("\n*** PACKER ECHOUE ***", flush=True)
