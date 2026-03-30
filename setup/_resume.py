"""Resume deployment: fix cert-manager + deploy Odoo + init + NAT"""
import paramiko, sys, os, time, json, urllib.request

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HOST = "51.77.216.79"
USER = "root"
PASS = "thoughtpolice"
WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAQAKGrYeME/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=UCuG1Mtp_pW8gwIO3MuyKzuobAER3tA85zusONbJh34"
START = time.time()

def fmt(s):
    m, s = divmod(int(s), 60)
    return f"{m}m{s:02d}s"

def log(msg):
    print(f"[{fmt(time.time()-START)}] {msg}", flush=True)

def webhook(text):
    data = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(WEBHOOK, data=data, headers={"Content-Type": "application/json; charset=UTF-8"})
    try: urllib.request.urlopen(req)
    except: pass

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
        for line in out.strip().split("\n")[-30:]:
            print(f"  {line}", flush=True)
    if err and code != 0:
        for line in err.strip().split("\n")[-10:]:
            print(f"  [ERR] {line}", flush=True)
    return out, err, code

webhook("*MSPR* - Reprise deploiement: fix cert-manager (quay.io 502 -> docker.io)")

# 1. Cleanup cert-manager failed release
log("=== Nettoyage cert-manager failed ===")
ssh_run("""
ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_ansible ubuntu@10.10.10.10 bash << 'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
helm uninstall cert-manager -n cert-manager 2>/dev/null || true
kubectl delete namespace cert-manager --timeout=60s 2>/dev/null || true
echo "cert-manager cleaned"
REMOTE
""", label="Cleanup cert-manager")

# 2. Update repo on Proxmox
log("=== Update repo ===")
ssh_run("""
cd /root/MSPR1-Deploy-Odoo && git pull --ff-only 2>&1 | tail -3
""", label="Git pull on Proxmox")

# 3. Re-run ansible deploy-odoo only
log("=== Lancement Ansible deploy-odoo ===")
ssh_run("""
cd /root/MSPR1-Deploy-Odoo/ansible
rm -f /tmp/ansible-deploy.log /tmp/ansible-exit-code
screen -dmS ansible bash -c 'ansible-playbook playbooks/deploy-odoo.yml -v > /tmp/ansible-deploy.log 2>&1; echo $? > /tmp/ansible-exit-code'
echo "Ansible lance"
""", label="Lancement ansible --tags deploy-odoo")

# 4. Poll
max_wait = 1200
poll = 30
waited = 0
while waited < max_wait:
    time.sleep(poll)
    waited += poll
    out, _, _ = ssh_run("""
    if [ -f /tmp/ansible-exit-code ]; then
        CODE=$(cat /tmp/ansible-exit-code)
        echo "FINISHED:$CODE"
        tail -20 /tmp/ansible-deploy.log
    else
        echo "RUNNING"
        tail -3 /tmp/ansible-deploy.log 2>/dev/null || echo "(vide)"
    fi
    """, label=f"Poll ({fmt(waited)})")

    if "FINISHED:" in out:
        code = out.split("FINISHED:")[1].split("\n")[0].strip()
        if code in ("0", "2"):
            log(f"Ansible termine (code {code})")
            break
        else:
            log(f"Ansible echoue (code {code})")
            ssh_run("tail -50 /tmp/ansible-deploy.log", label="Error log")
            webhook(f"*ECHEC* Ansible (code {code})")
            sys.exit(1)
else:
    webhook("*ECHEC* Ansible timeout")
    sys.exit(1)

webhook("*[5/7]* Ansible deploy-odoo OK")

# 5. Init Odoo
log("=== Init Odoo + IngressRoute ===")
out, err, code = ssh_run("""
ssh -o StrictHostKeyChecking=no -i /root/.ssh/id_ansible ubuntu@10.10.10.10 bash << 'REMOTE'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

echo "=== Attente pod Odoo ==="
for i in $(seq 1 30); do
    READY=$(kubectl get pods -n odoo -l app=odoo --no-headers 2>/dev/null | grep Running | wc -l)
    if [ "$READY" -ge 1 ]; then echo "Pod Odoo running"; break; fi
    echo "  attente... ($i)"
    sleep 10
done

echo ""
echo "=== Init base Odoo ==="
kubectl exec -n odoo deployment/odoo -- odoo -d odoo -i base --stop-after-init \
    --db_host=postgres --db_user=odoo --db_password='Ch4ng3M3!Pg2026' 2>&1 | tail -5

echo ""
echo "=== Restart Odoo ==="
kubectl rollout restart deployment/odoo -n odoo
sleep 20

echo ""
echo "=== IngressRoute HTTP ==="
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
echo "=== Etat ==="
kubectl get pods -n odoo -o wide
kubectl get pods -n cert-manager -o wide 2>/dev/null
echo "INIT_OK"
REMOTE
""", timeout=600, label="Init Odoo + IngressRoute")

# 6. NAT
log("=== NAT ===")
ssh_run("""
CP="10.10.10.10"
iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to-destination ${CP}:80 2>/dev/null || \
    iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to-destination ${CP}:80
iptables -t nat -C PREROUTING -i vmbr0 -p tcp --dport 443 -j DNAT --to-destination ${CP}:443 2>/dev/null || \
    iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 443 -j DNAT --to-destination ${CP}:443
netfilter-persistent save > /dev/null 2>&1
echo "NAT OK"
""", label="NAT port-forwarding")

# 7. Verify
log("=== Verification ===")
time.sleep(30)
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
""", label="Verification Odoo")

total = time.time() - START
ok = "ODOO_OK" in out

if ok:
    webhook(f"*MSPR COGIP - Deploiement termine !*\nTemps reprise: *{fmt(total)}*\nOdoo accessible sur http://odoo.local\nLogin: admin / admin")
else:
    webhook(f"*MSPR COGIP* - Reprise en {fmt(total)}, mais Odoo ne repond pas encore (404/timeout)")

log(f"TERMINE en {fmt(total)} - Odoo: {'OK' if ok else 'ATTENTION'}")
