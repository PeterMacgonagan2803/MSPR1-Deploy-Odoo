#!/usr/bin/env python3
"""Test SSH ubuntu@10.10.10.99 via bastion root@Proxmox (jump host)."""
import sys
import time

import paramiko

BASTION = "51.77.216.79"
BASTION_USER = "root"
BASTION_PASS = "thoughtpolice"
VM_HOST = "10.10.10.99"
VM_USER = "ubuntu"
VM_PASS = "ubuntu"
WAIT_SEC = 25


def main():
    print(f"Attente {WAIT_SEC}s puis test SSH {VM_USER}@{VM_HOST} via {BASTION}...", flush=True)
    time.sleep(WAIT_SEC)

    jump = paramiko.SSHClient()
    jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump.connect(BASTION, username=BASTION_USER, password=BASTION_PASS, timeout=30)
    print("Bastion OK.", flush=True)

    transport = jump.get_transport()
    if transport is None:
        print("ERREUR: pas de transport SSH bastion", file=sys.stderr)
        sys.exit(1)

    dest = (VM_HOST, 22)
    local = ("", 0)
    chan = transport.open_channel("direct-tcpip", dest, local)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            VM_HOST,
            username=VM_USER,
            password=VM_PASS,
            sock=chan,
            timeout=20,
            allow_agent=False,
            look_for_keys=False,
        )
    except Exception as e:
        print(f"ECHEC SSH vers la VM: {e}", flush=True)
        jump.close()
        sys.exit(1)

    stdin, stdout, stderr = client.exec_command("hostname && ip -4 addr show | head -20")
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print("--- sortie distante ---", flush=True)
    print(out, end="", flush=True)
    if err:
        print("stderr:", err[:800], flush=True)

    client.close()
    jump.close()
    print("SSH_VM: OK", flush=True)


if __name__ == "__main__":
    main()
