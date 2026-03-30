import paramiko
import sys
import time

HOST = "51.77.216.79"
USER = "root"
PASS = "thoughtpolice"

def run(cmd, timeout=600):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    ssh.close()
    if out:
        print(out, end="")
    if err and code != 0:
        print(err, end="", file=sys.stderr)
    return code

print("=== [1/6] Adding SSH keys to VMs via cloud-init ===")
run("""
PROXKEY=$(cat /root/.ssh/id_ansible.pub)
USERKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHcjlUzYzCiRGTe+TWekFc/RmLX13pcXijChNYZOiBBw mspr-cogip"
TMPFILE=$(mktemp)
echo "$USERKEY" > $TMPFILE
echo "$PROXKEY" >> $TMPFILE
for vmid in 200 201 202 203; do
    qm set $vmid --sshkeys $TMPFILE 2>&1
    echo "VM $vmid keys updated"
done
rm -f $TMPFILE
""")

print("\n=== [2/6] Regenerate cloud-init and reboot VMs ===")
run("""
for vmid in 200 201 202 203; do
    qm cloudinit update $vmid 2>/dev/null
    qm reboot $vmid 2>&1
    echo "VM $vmid rebooting"
done
""")

print("\n=== [3/6] Wait for VMs to come up (60s) ===")
time.sleep(60)

code = run("""
for ip in 10.10.10.10 10.10.10.11 10.10.10.12 10.10.10.13; do
    ping -c 2 -W 3 $ip > /dev/null 2>&1 && echo "$ip OK" || echo "$ip WAITING"
done
""")

print("\n=== [4/6] Test SSH to VMs ===")
run("""
for ip in 10.10.10.10 10.10.10.11 10.10.10.12 10.10.10.13; do
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /root/.ssh/id_ansible ubuntu@$ip "echo $ip SSH_OK" 2>/dev/null || echo "$ip SSH_FAIL"
done
""")

print("\n=== [5/6] Update Ansible inventory for Proxmox execution ===")
run("""
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
echo "Inventory written"
""")

print("\n=== [6/6] Install Ansible Galaxy collections ===")
run("""
cd /root/MSPR1-Deploy-Odoo/ansible
ansible-galaxy collection install -r requirements.yml --force 2>&1 | tail -5
echo "Collections installed"
""")

print("\n=== Setup complete! Ready for Ansible playbook ===")
