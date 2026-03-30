"""
MSPR COGIP - Script de deploiement complet depuis zero.
Reset Proxmox + Template + Terraform + Ansible + Odoo Init + NAT
Envoie des notifications webhook a chaque etape.
"""
import paramiko
import sys
import os
import time
import json
import re
import urllib.request
import subprocess

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HOST = "51.77.216.79"
USER = "root"
PASS = "thoughtpolice"
WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAKGrYeME/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=UCuG1Mtp_pW8gwIO3MuyKzuobAER3tA85zusONbJh34"

TOTAL_START = time.time()
step_times = {}

def elapsed():
    return time.time() - TOTAL_START

def fmt(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"

def log(msg):
    print(f"[{fmt(elapsed())}] {msg}", flush=True)

def webhook(text):
    data = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(WEBHOOK_URL, data=data, headers={"Content-Type": "application/json; charset=UTF-8"})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        log(f"Webhook erreur: {e}")

def ssh_run(cmd, timeout=900, label=""):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    log(label)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    ssh.close()
    if out:
        for line in out.strip().split("\n")[-40:]:
            print(f"  {line}", flush=True)
    if err and code != 0:
        for line in err.strip().split("\n")[-10:]:
            print(f"  [ERR] {line}", flush=True)
    return out, err, code

def ssh_run_must(cmd, timeout=900, label=""):
    out, err, code = ssh_run(cmd, timeout, label)
    if code != 0:
        log(f"ECHEC: {label}")
        webhook(f"*ECHEC* etape: {label}\n```\n{err[:500]}\n```")
        sys.exit(1)
    return out

def terraform(args, cwd):
    log(f"Terraform: {args}")
    result = subprocess.run(f"terraform {args}", cwd=cwd, shell=True, capture_output=True, text=True, timeout=600)
    if result.stdout:
        for line in result.stdout.strip().split("\n")[-20:]:
            print(f"  {line}", flush=True)
    if result.returncode != 0:
        for line in (result.stderr or "").strip().split("\n")[-15:]:
            print(f"  [ERR] {line}", flush=True)
    return result.returncode

tf_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "terraform"))

# =====================================================================
log("="*60)
log("MSPR COGIP - DEPLOIEMENT COMPLET DEPUIS ZERO")
log("="*60)
webhook("*MSPR COGIP* - Deploiement complet lance depuis zero...")

# =====================================================================
# ETAPE 1: RESET PROXMOX
# =====================================================================
t = time.time()
webhook("*[1/7]* Reset Proxmox en cours...")

ssh_run_must("""
echo "--- Arret et suppression de toutes les VMs ---"
for vmid in 200 201 202 203; do
    if qm status $vmid &>/dev/null; then
        qm stop $vmid --timeout 15 2>/dev/null || true
        sleep 2
        qm destroy $vmid --purge 2>/dev/null && echo "VM $vmid detruite" || echo "VM $vmid: echec destruction"
    else
        echo "VM $vmid: absente"
    fi
done

echo ""
echo "--- Suppression du template 9000 ---"
if qm status 9000 &>/dev/null; then
    qm destroy 9000 --purge 2>/dev/null && echo "Template 9000 detruit" || echo "Template 9000: echec"
else
    echo "Template 9000: absent"
fi

echo ""
echo "--- Nettoyage iptables PREROUTING ---"
iptables -t nat -F PREROUTING 2>/dev/null || true

echo "--- Setup NAT MASQUERADE pour acces internet VMs ---"
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -C POSTROUTING -s 10.10.10.0/24 -o vmbr0 -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -o vmbr0 -j MASQUERADE
echo "iptables NAT OK"

echo "--- Nettoyage locks ---"
rm -f /var/lock/pve-manager/pve-storage-* 2>/dev/null || true

echo "--- Nettoyage ancien clone ---"
rm -rf /root/MSPR1-Deploy-Odoo
rm -f /root/.ssh/known_hosts

echo "--- Verification ---"
qm list 2>/dev/null || echo "Aucune VM"
echo "RESET_OK"
""", label="[1/7] RESET PROXMOX")

step_times["1_reset"] = time.time() - t
webhook(f"*[1/7]* Reset Proxmox OK ({fmt(step_times['1_reset'])})")

# =====================================================================
# ETAPE 2: TEMPLATE VM
# =====================================================================
t = time.time()
webhook("*[2/7]* Creation template VM en cours...")

ssh_run_must("""
set -e
TEMPLATE_ID=9000
STORAGE="local"
BRIDGE="vmbr1"
CLOUD_IMAGE="/tmp/jammy-server-cloudimg-amd64.img"

echo "[1/7] Telechargement image cloud Ubuntu 22.04..."
wget -q -O "$CLOUD_IMAGE" "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
echo "  OK"

echo "[2/7] Installation paquets dans l'image..."
dpkg -l libguestfs-tools &>/dev/null || apt-get install -y -qq libguestfs-tools > /dev/null 2>&1
virt-customize -a "$CLOUD_IMAGE" \
    --install qemu-guest-agent,curl,wget,nfs-common,open-iscsi,jq,unzip \
    --run-command 'systemctl enable qemu-guest-agent' \
    --run-command 'dpkg --configure -a' \
    --run-command 'apt --fix-broken install -y' \
    --run-command 'apt-get clean' 2>&1 | tail -5
echo "  OK"

echo "[3/7] Redimensionnement disque 30G..."
qemu-img resize "$CLOUD_IMAGE" 30G

echo "[4/7] Creation VM..."
qm create $TEMPLATE_ID \
    --name "ubuntu-k3s-template" \
    --description "Ubuntu 22.04 LTS - Template K3s MSPR COGIP" \
    --memory 4096 --cores 2 --cpu host \
    --net0 virtio,bridge=$BRIDGE \
    --scsihw virtio-scsi-single \
    --agent enabled=1 --ostype l26 --onboot 0

echo "[5/7] Import disque..."
qm importdisk $TEMPLATE_ID "$CLOUD_IMAGE" $STORAGE --format qcow2 2>&1 | tail -2

echo "[6/7] Configuration..."
qm set $TEMPLATE_ID --scsi0 ${STORAGE}:${TEMPLATE_ID}/vm-${TEMPLATE_ID}-disk-0.qcow2
qm set $TEMPLATE_ID --ide2 ${STORAGE}:cloudinit
qm set $TEMPLATE_ID --boot order=scsi0
qm set $TEMPLATE_ID --serial0 socket --vga serial0

echo "[7/7] Conversion en template..."
qm template $TEMPLATE_ID

rm -f "$CLOUD_IMAGE"
echo "TEMPLATE_OK"
""", timeout=600, label="[2/7] CREATION TEMPLATE VM")

step_times["2_template"] = time.time() - t
webhook(f"*[2/7]* Template VM cree ({fmt(step_times['2_template'])})")

# =====================================================================
# ETAPE 3: TERRAFORM
# =====================================================================
t = time.time()
webhook("*[3/7]* Terraform apply en cours...")

for f in ["terraform.tfstate", "terraform.tfstate.backup"]:
    p = os.path.join(tf_dir, f)
    if os.path.exists(p):
        os.remove(p)

rc = terraform("init -upgrade -input=false", tf_dir)
if rc != 0:
    webhook("*ECHEC* Terraform init")
    sys.exit(1)

rc = terraform("apply -auto-approve -parallelism=1 -input=false", tf_dir)
if rc != 0:
    log("Premiere tentative Terraform echouee, nettoyage et retry...")
    ssh_run("""
    for vmid in 200 201 202 203; do
        qm stop $vmid --timeout 10 2>/dev/null || true
        qm destroy $vmid --purge 2>/dev/null || true
    done
    rm -f /var/lock/pve-manager/pve-storage-*
    echo "Cleanup done"
    """, label="Nettoyage VMs partielles")
    for f in ["terraform.tfstate", "terraform.tfstate.backup"]:
        p = os.path.join(tf_dir, f)
        if os.path.exists(p):
            os.remove(p)
    time.sleep(5)
    rc = terraform("apply -auto-approve -parallelism=1 -input=false", tf_dir)
    if rc != 0:
        webhook("*ECHEC* Terraform apply (2eme tentative)")
        sys.exit(1)

step_times["3_terraform"] = time.time() - t
webhook(f"*[3/7]* Terraform OK - 4 VMs creees ({fmt(step_times['3_terraform'])})")

# =====================================================================
# ETAPE 4: SETUP ANSIBLE
# =====================================================================
t = time.time()
webhook("*[4/7]* Setup Ansible en cours...")

ssh_run_must("""
echo "--- Install Ansible ---"
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq ansible python3-pip git screen > /dev/null 2>&1
pip3 install --break-system-packages kubernetes PyYAML jsonpatch 2>&1 | tail -1
echo "Ansible: $(ansible --version | head -1)"

echo "--- Clone repo ---"
cd /root
rm -rf MSPR1-Deploy-Odoo
git clone --depth 1 https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo.git 2>&1 | tail -2

echo "--- Cle SSH ---"
rm -f /root/.ssh/id_ansible /root/.ssh/id_ansible.pub
ssh-keygen -t ed25519 -f /root/.ssh/id_ansible -N '' -q
echo "Cle OK"
""", label="[4/7] Installation Ansible")

log("Attente boot VMs (45s)...")
time.sleep(45)

ssh_run_must("""
echo "--- Injection cles SSH ---"
PROXKEY=$(cat /root/.ssh/id_ansible.pub)
USERKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHcjlUzYzCiRGTe+TWekFc/RmLX13pcXijChNYZOiBBw mspr-cogip"
TMPFILE=$(mktemp)
echo "$USERKEY" > $TMPFILE
echo "$PROXKEY" >> $TMPFILE
for vmid in 200 201 202 203; do
    qm set $vmid --sshkeys $TMPFILE 2>&1 | grep -v sshkeys || true
    qm cloudinit update $vmid 2>/dev/null
    echo "VM $vmid: cles OK"
done
rm -f $TMPFILE

echo "--- Reboot VMs ---"
for vmid in 200 201 202 203; do
    qm reboot $vmid 2>&1 || qm stop $vmid 2>/dev/null && sleep 1 && qm start $vmid 2>/dev/null
    echo "VM $vmid: reboot"
done
""", label="Injection cles SSH + reboot")

log("Attente reboot VMs (90s)...")
time.sleep(90)

ssh_run("""
rm -f /root/.ssh/known_hosts
echo "--- Test SSH (avec retries) ---"
ALL_OK=true
for ip in 10.10.10.10 10.10.10.11 10.10.10.12 10.10.10.13; do
    OK=false
    for i in 1 2 3 4 5 6 7 8 9 10; do
        if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /root/.ssh/id_ansible ubuntu@$ip "echo OK" 2>/dev/null; then
            echo "$ip SSH OK"
            OK=true
            break
        fi
        sleep 10
    done
    if [ "$OK" = "false" ]; then
        echo "$ip SSH FAIL"
        ALL_OK=false
    fi
done
if [ "$ALL_OK" = "false" ]; then
    echo "ATTENTION: Certaines VMs ne sont pas accessibles"
    exit 1
fi
echo "ALL_SSH_OK"
""", timeout=300, label="Test SSH vers toutes les VMs")

log("Reparation dpkg + apt fix-broken sur toutes les VMs...")
ssh_run_must("""
for ip in 10.10.10.10 10.10.10.11 10.10.10.12 10.10.10.13; do
    echo "--- Fix $ip ---"
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i /root/.ssh/id_ansible ubuntu@$ip \
        'sudo dpkg --configure -a; sudo apt --fix-broken install -y; sudo apt-get update -qq' 2>&1 | tail -3
    echo "$ip: OK"
done
echo "DPKG_FIX_DONE"
""", timeout=600, label="Fix dpkg sur toutes les VMs")

log("Installation kubernetes Python sur le control plane...")
ssh_run_must("""
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i /root/.ssh/id_ansible ubuntu@10.10.10.10 bash -c '
sudo apt-get update -qq 2>&1 | tail -1
sudo apt-get install -y python3-kubernetes python3-pip python3-yaml python3-jsonpatch 2>&1 | tail -5
python3 -c "import kubernetes; print(kubernetes.__version__)" 2>&1
echo K8S_PY_OK
'
""", timeout=300, label="Install kubernetes Python lib sur CP")

ssh_run_must("""
cd /root/MSPR1-Deploy-Odoo/ansible

mkdir -p inventory
cat > inventory/hosts.yml << 'INVENTORY'
---
all:
  vars:
    ansible_user: ubuntu
    ansible_ssh_private_key_file: /root/.ssh/id_ansible
    ansible_python_interpreter: /usr/bin/python3
    k3s_version: "v1.29.2+k3s1"
    odoo_domain: "odoo.local"
  children:
    k3s_server:
      hosts:
        k3s-control-plane:
          ansible_host: 10.10.10.10
          k3s_role: server
    k3s_agents:
      hosts:
        k3s-worker-1:
          ansible_host: 10.10.10.11
          k3s_role: agent
        k3s-worker-2:
          ansible_host: 10.10.10.12
          k3s_role: agent
    nfs:
      hosts:
        nfs-server:
          ansible_host: 10.10.10.13
          nfs_export_path: /srv/nfs/k8s
    k3s_cluster:
      children:
        k3s_server:
        k3s_agents:
INVENTORY

ln -sf ../group_vars inventory/group_vars 2>/dev/null || true
ln -sf ../group_vars playbooks/group_vars 2>/dev/null || true
sed -i 's/stdout_callback = yaml/stdout_callback = default/' ansible.cfg 2>/dev/null || true
ansible-galaxy collection install -r requirements.yml --force 2>&1 | tail -3
echo "SETUP_ANSIBLE_OK"
""", label="Configuration inventaire + Galaxy collections")

step_times["4_setup"] = time.time() - t
webhook(f"*[4/7]* Setup Ansible OK ({fmt(step_times['4_setup'])})")

# =====================================================================
# ETAPE 5: ANSIBLE PLAYBOOK
# =====================================================================
t = time.time()
webhook("*[5/7]* Ansible playbook en cours (K3s + NFS + Odoo)...")

ssh_run("""
cd /root/MSPR1-Deploy-Odoo/ansible
rm -f /tmp/ansible-deploy.log /tmp/ansible-exit-code
screen -dmS ansible bash -c 'ansible-playbook playbooks/site.yml -v > /tmp/ansible-deploy.log 2>&1; echo $? > /tmp/ansible-exit-code'
echo "Ansible lance en background"
""", label="[5/7] Lancement Ansible playbook")

max_wait = 1800
poll = 30
waited = 0
while waited < max_wait:
    time.sleep(poll)
    waited += poll
    out, _, _ = ssh_run(f"""
    if [ -f /tmp/ansible-exit-code ]; then
        CODE=$(cat /tmp/ansible-exit-code)
        echo "FINISHED:$CODE"
        tail -15 /tmp/ansible-deploy.log
    else
        echo "RUNNING"
        tail -3 /tmp/ansible-deploy.log 2>/dev/null || echo "(log vide)"
    fi
    """, label=f"Poll Ansible ({fmt(waited)})")

    if "FINISHED:" in out:
        code = out.split("FINISHED:")[1].split("\n")[0].strip()
        if code == "0":
            log("Ansible termine avec succes!")
            break
        elif code == "2":
            recap_out, _, _ = ssh_run("grep -A 20 'PLAY RECAP' /tmp/ansible-deploy.log | tail -20", label="Ansible PLAY RECAP")
            failed_counts = re.findall(r'failed=(\d+)', recap_out)
            total_failed = sum(int(x) for x in failed_counts)
            if total_failed == 0:
                log("Ansible code 2 mais 0 failed total, on continue")
                break
            log(f"Ansible echoue: {total_failed} task(s) failed")
            ssh_run("tail -60 /tmp/ansible-deploy.log", label="Ansible error log")
            webhook(f"*ECHEC* Ansible playbook - {total_failed} tasks failed\n```\n{recap_out[:500]}\n```")
            sys.exit(1)
        else:
            log(f"Ansible echoue (code {code})")
            ssh_run("tail -50 /tmp/ansible-deploy.log", label="Ansible error log")
            webhook(f"*ECHEC* Ansible playbook (code {code}) apres {fmt(elapsed())}")
            sys.exit(1)
else:
    webhook(f"*ECHEC* Ansible timeout apres {fmt(elapsed())}")
    sys.exit(1)

step_times["5_ansible"] = time.time() - t
webhook(f"*[5/7]* Ansible OK - K3s + Odoo deployes ({fmt(step_times['5_ansible'])})")

# =====================================================================
# ETAPE 6: INIT ODOO + INGRESS HTTP + NAT
# =====================================================================
t = time.time()
webhook("*[6/7]* Initialisation Odoo + port-forwarding...")

ssh_run_must("""
ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_ansible ubuntu@10.10.10.10 bash << 'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

echo "=== Attente pods Odoo ==="
for i in $(seq 1 30); do
    RUNNING=$(kubectl get pods -n odoo -l app=odoo --no-headers 2>/dev/null | grep Running | wc -l)
    if [ "$RUNNING" -ge 1 ]; then
        echo "Pod Odoo running"
        break
    fi
    echo "  attente... ($i)"
    sleep 10
done

echo ""
echo "=== Init base Odoo (odoo -i base) ==="
kubectl exec -n odoo deployment/odoo -- odoo -d odoo -i base --stop-after-init \
    --db_host=postgres --db_user=odoo --db_password='Ch4ng3M3!Pg2026' 2>&1 | tail -5

echo ""
echo "=== Restart pod Odoo ==="
kubectl rollout restart deployment/odoo -n odoo
sleep 15

echo ""
echo "=== Creation IngressRoute HTTP ==="
cat > /tmp/odoo-http-route.yaml << 'YAML'
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: odoo-http
  namespace: odoo
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`odoo.local`)
      kind: Rule
      services:
        - name: odoo
          port: 8069
YAML
kubectl apply -f /tmp/odoo-http-route.yaml

echo ""
echo "=== Etat cluster ==="
kubectl get nodes
kubectl get pods -n odoo -o wide
echo "INIT_ODOO_OK"
REMOTE
""", timeout=600, label="[6/7] Init Odoo + IngressRoute HTTP")

ssh_run_must("""
CP="10.10.10.10"
iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to-destination ${CP}:80 2>/dev/null || \
    iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to-destination ${CP}:80
iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 443 -j DNAT --to-destination ${CP}:443 2>/dev/null || \
    iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 443 -j DNAT --to-destination ${CP}:443
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iptables-persistent > /dev/null 2>&1
netfilter-persistent save > /dev/null 2>&1
echo "NAT_OK: 80+443 -> ${CP}"
""", label="Port-forwarding iptables")

step_times["6_init"] = time.time() - t
webhook(f"*[6/7]* Init Odoo + NAT OK ({fmt(step_times['6_init'])})")

# =====================================================================
# ETAPE 7: VERIFICATION FINALE
# =====================================================================
t = time.time()
webhook("*[7/7]* Verification finale...")

log("Attente 30s pour le redemarrage du pod Odoo...")
time.sleep(30)

odoo_ok = False
out, _, _ = ssh_run("""
for i in 1 2 3 4 5 6 7 8 9 10; do
    CODE=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: odoo.local' http://10.10.10.10:80/ --max-time 10)
    echo "Tentative $i: HTTP $CODE"
    if [ "$CODE" = "200" ] || [ "$CODE" = "303" ]; then
        echo "ODOO_OK"
        exit 0
    fi
    sleep 15
done
echo "ODOO_FAIL"
exit 1
""", label="[7/7] Verification Odoo accessible")

odoo_ok = "ODOO_OK" in out
step_times["7_verify"] = time.time() - t
TOTAL = time.time() - TOTAL_START

# =====================================================================
# RECAPITULATIF
# =====================================================================
print(f"\n{'='*60}", flush=True)
print(f"RECAPITULATIF DU DEPLOIEMENT", flush=True)
print(f"{'='*60}", flush=True)
for key, label in [("1_reset","Reset Proxmox"),("2_template","Template VM"),("3_terraform","Terraform apply"),("4_setup","Setup Ansible"),("5_ansible","Ansible playbook"),("6_init","Init Odoo + NAT"),("7_verify","Verification")]:
    print(f"  {label:25s}: {fmt(step_times.get(key, 0))}", flush=True)
print(f"  {'─'*40}", flush=True)
print(f"  {'TOTAL':25s}: {fmt(TOTAL)}", flush=True)
status = "OK" if odoo_ok else "ATTENTION"
print(f"  Statut Odoo: {status}", flush=True)
print(f"{'='*60}", flush=True)

if odoo_ok:
    webhook_msg = f"""*MSPR COGIP - Deploiement termine avec succes !*

Temps total : *{fmt(TOTAL)}*

Etapes :
- Reset Proxmox : {fmt(step_times.get('1_reset',0))}
- Template VM : {fmt(step_times.get('2_template',0))}
- Terraform (4 VMs) : {fmt(step_times.get('3_terraform',0))}
- Setup Ansible : {fmt(step_times.get('4_setup',0))}
- Ansible (K3s + Odoo) : {fmt(step_times.get('5_ansible',0))}
- Init Odoo + NAT : {fmt(step_times.get('6_init',0))}
- Verification : {fmt(step_times.get('7_verify',0))}

Odoo accessible sur http://odoo.local
Login: admin / admin"""
else:
    webhook_msg = f"*MSPR COGIP* - Deploiement termine en {fmt(TOTAL)} mais Odoo n'est pas encore accessible. Verification manuelle requise."

webhook(webhook_msg)
log("DEPLOIEMENT TERMINE!")
