import paramiko, logging
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("51.77.216.79", username="root", password="thoughtpolice", timeout=10)
cmd = (
    "for ip in 10.10.10.10 10.10.10.11 10.10.10.12 10.10.10.13; do "
    "nc -z -w3 $ip 22 2>/dev/null && echo \"$ip:SSH_OPEN\" || echo \"$ip:SSH_CLOSED\"; "
    "done; echo '---'; qm list"
)
_, out, _ = c.exec_command(cmd)
print(out.read().decode())
c.close()
