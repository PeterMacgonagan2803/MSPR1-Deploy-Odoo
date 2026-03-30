import paramiko
import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HOST = "51.77.216.79"
USER = "root"
PASS = "thoughtpolice"

cmd = sys.argv[1] if len(sys.argv) > 1 else "echo no command"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

transport = ssh.get_transport()
channel = transport.open_session()
channel.exec_command(cmd)
channel.shutdown_write()

import time
time.sleep(1)

if channel.recv_ready():
    print(channel.recv(65536).decode("utf-8", errors="replace"), end="")

ssh.close()
print("Command sent to remote server")
