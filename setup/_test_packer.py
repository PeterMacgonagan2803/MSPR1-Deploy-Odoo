"""Test Packer sur Proxmox - installe Packer, telecharge ISO, lance le build."""
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
    for line in out.strip().split("\n")[-50:]:
        print(f"  {line}", flush=True)
    if code != 0:
        for line in err.strip().split("\n")[-15:]:
            print(f"  [ERR] {line}", flush=True)
        print(f"  EXIT CODE: {code}", flush=True)
    return out, err, code

# STEP 1: Install Packer
ssh_run("""
if ! command -v packer &>/dev/null; then
    echo 'Installing Packer...'
    wget -qO- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg 2>/dev/null
    echo 'deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com bookworm main' > /etc/apt/sources.list.d/hashicorp.list
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq packer > /dev/null 2>&1
fi
packer --version
""", label="INSTALL PACKER")

# STEP 2: Download ISO
ssh_run("""
ISO_DIR='/var/lib/vz/template/iso'
ISO_FILE='ubuntu-22.04.5-live-server-amd64.iso'
mkdir -p "$ISO_DIR"
if [ -f "$ISO_DIR/$ISO_FILE" ]; then
    echo "ISO deja presente"
    ls -lh "$ISO_DIR/$ISO_FILE"
else
    echo "Telechargement ISO (~2.6 Go)..."
    wget -q -O "$ISO_DIR/$ISO_FILE" "https://releases.ubuntu.com/22.04/$ISO_FILE"
    ls -lh "$ISO_DIR/$ISO_FILE"
fi
echo "ISO_OK"
""", timeout=600, label="DOWNLOAD ISO")

# STEP 3: Pull repo + generate hash + fix user-data
ssh_run(r"""
cd /root
if [ -d MSPR1-Deploy-Odoo ]; then
    cd MSPR1-Deploy-Odoo && git pull --ff-only 2>&1 | tail -3
else
    git clone --depth 1 https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo.git 2>&1 | tail -3
    cd MSPR1-Deploy-Odoo
fi

HASH=$(openssl passwd -6 ubuntu)
echo "Hash genere: ${HASH:0:20}..."
sed -i "s|__UBUNTU_HASH__|${HASH}|" packer/http/user-data
echo "user-data mis a jour:"
cat packer/http/user-data
echo "PREP_OK"
""", label="PULL REPO + HASH")

# STEP 4: Destroy test template 9001 if exists
ssh_run("""
qm stop 9001 --timeout 5 2>/dev/null || true
qm destroy 9001 --purge 2>/dev/null && echo "Template 9001 detruit" || echo "Template 9001 absent, OK"
""", label="CLEANUP 9001")

# STEP 5: Packer init + build (VMID 9001 pour ne pas casser le 9000 actuel)
print("\n=== LANCEMENT PACKER BUILD (VMID 9001) ===", flush=True)
print("Cela prend ~15-20 min (autoinstall Ubuntu + provisioner)...", flush=True)

ssh_run("""
cd /root/MSPR1-Deploy-Odoo/packer

echo "=== Packer init ==="
packer init . 2>&1

echo ""
echo "=== Packer build ==="
PACKER_LOG=1 packer build \
    -var "proxmox_password=thoughtpolice" \
    -var "proxmox_node=ns3139245" \
    -var "vm_id=9001" \
    . 2>&1 | tail -80

echo "BUILD_EXIT: $?"
""", timeout=1800, label="PACKER BUILD")

# STEP 6: Verify
out, _, code = ssh_run("""
qm list | grep 9001 && echo "PACKER_SUCCESS" || echo "PACKER_FAIL"
""", label="VERIFY TEMPLATE 9001")

if "PACKER_SUCCESS" in out:
    print("\n*** PACKER TEST REUSSI - Template 9001 cree ***", flush=True)
else:
    print("\n*** PACKER TEST ECHOUE ***", flush=True)
