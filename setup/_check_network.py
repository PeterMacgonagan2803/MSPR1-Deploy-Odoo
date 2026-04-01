import paramiko, logging, json
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("51.77.216.79", username="root", password="thoughtpolice", timeout=10)

def exec_vm(vmid, bash_cmd):
    cmd = f"qm guest exec {vmid} -- bash -c '{bash_cmd}'"
    _, out, _ = c.exec_command(cmd)
    raw = out.read().decode()
    try:
        d = json.loads(raw)
        return d.get("out-data", "") + d.get("err-data", "")
    except:
        return raw

# Voir la ligne de commande kernel réelle du VM au boot
print("=== GRUB cmdline VM200 ===")
print(exec_vm(200, "cat /proc/cmdline"))

# Voir ce que cloud-init a lu comme network-config
print("\n=== cloud-init network-config source ===")
print(exec_vm(200, "cat /var/lib/cloud/instance/network-config.json 2>/dev/null || cat /var/lib/cloud/instance/network-config 2>/dev/null"))

c.close()
