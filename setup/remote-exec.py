import paramiko
import sys
import time
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def ssh_exec(host, user, password, command, timeout=900):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=10)
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    exit_code = stdout.channel.recv_exit_status()
    ssh.close()
    return out, err, exit_code

HOST = "51.77.216.79"
USER = "root"
PASS = "thoughtpolice"

if len(sys.argv) < 2:
    print("Usage: python remote-exec.py <command>")
    sys.exit(1)

cmd = sys.argv[1]
out, err, code = ssh_exec(HOST, USER, PASS, cmd)
if out:
    print(out, end="")
if err:
    print(err, end="", file=sys.stderr)
sys.exit(code)
