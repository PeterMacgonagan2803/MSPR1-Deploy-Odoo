# Guide de démarrage — Serveur OVH + Proxmox

## Checklist complète (dans l'ordre)

- [x] **Étape 0** — Installer les outils sur ton PC
- [x] **Étape 1** — Premier accès à Proxmox et configuration de base
- [x] **Étape 2** — Créer un API Token Proxmox (pour Terraform)
- [x] **Étape 3** — Configurer le réseau Proxmox (NAT vmbr1)
- [x] **Étape 4** — Générer ta paire de clés SSH
- [x] **Étape 5** — Remplir les fichiers de configuration (tfvars)
- [x] **Étape 6** — Créer le template VM (image cloud Ubuntu)
- [x] **Étape 7** — Lancer Terraform (déployer les 4 VMs)
- [x] **Étape 8** — Lancer Ansible (cluster K3s + Odoo)
- [x] **Étape 9** — Port-forwarding + accéder à Odoo

---

## Étape 0 : Installer les outils sur ton PC

Lance le script `install-tools.ps1` (en tant qu'admin) :

```powershell
cd setup
.\install-tools.ps1
```

Cela installe : Terraform, Packer, Helm, kubectl, Python, Paramiko.

**Vérification :**
```powershell
terraform --version
helm version
kubectl version --client
python --version
```

---

## Étape 1 : Premier accès à Proxmox

1. Connecte-toi à l'interface web Proxmox :
   ```
   https://<IP-SERVEUR-OVH>:8006
   ```
2. Identifiants par défaut OVH : `root` + le mot de passe défini lors de la commande
3. Note ces informations :
   - **IP publique du serveur** : `51.77.216.79`
   - **Nom du noeud Proxmox** : `ns3139245`
   - **Pool de stockage** : `local` (type dir)

---

## Étape 2 : Créer un API Token Proxmox

L'API Token permet à Terraform de communiquer avec Proxmox.

1. Via SSH sur le serveur :
   ```bash
   pveum user token add root@pam terraform --privsep 0
   pveum acl modify / -user root@pam -role Administrator
   ```
2. **COPIE le Token Secret** qui s'affiche (il ne sera plus jamais affiché !)
3. Note :
   - **Token ID** : `root@pam!terraform`
   - **Token Secret** : `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

---

## Étape 3 : Configurer le réseau Proxmox (NAT)

Avec une seule IP publique, il faut créer un réseau interne NAT pour les VMs.

```bash
ssh root@<IP-SERVEUR-OVH>
# Copie et exécute le script
curl -fsSL https://raw.githubusercontent.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo/main/setup/configure-network.sh -o /root/configure-network.sh
bash /root/configure-network.sh
```

Les VMs auront des IPs en `10.10.10.x` et accéderont à internet via NAT.

---

## Étape 4 : Générer ta paire de clés SSH

```powershell
ssh-keygen -t ed25519 -C "mspr-cogip" -f $env:USERPROFILE\.ssh\id_mspr
```

- Clé privée : `~/.ssh/id_mspr`
- Clé publique : `~/.ssh/id_mspr.pub`

Affiche la clé publique :
```powershell
Get-Content $env:USERPROFILE\.ssh\id_mspr.pub
```

---

## Étape 5 : Remplir les fichiers de configuration

```powershell
cd C:\Users\PC-HUGO\MSPR\terraform
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Remplis avec tes vraies valeurs :
```hcl
proxmox_url      = "https://<IP>:8006/api2/json"
proxmox_user     = "root@pam"
proxmox_password = "<MOT_DE_PASSE>"
proxmox_node     = "<NOM_NOEUD>"

template_name  = "ubuntu-k3s-template"
storage_pool   = "local"
network_bridge = "vmbr1"

ssh_user       = "ubuntu"
ssh_public_key = "<CONTENU de id_mspr.pub>"

gateway    = "10.10.10.1"
nameserver = "8.8.8.8"

ip_control_plane = "10.10.10.10/24"
ip_worker_1      = "10.10.10.11/24"
ip_worker_2      = "10.10.10.12/24"
ip_nfs           = "10.10.10.13/24"

ssh_private_key_path = "~/.ssh/id_mspr"
k3s_version          = "v1.29.2+k3s1"
odoo_domain          = "odoo.local"
nfs_export_path      = "/srv/nfs/k8s"
```

---

## Étape 6 : Créer le template VM

On utilise l'API Proxmox pour télécharger une image cloud Ubuntu et créer le template.

**Option A — Script automatique (depuis le serveur Proxmox via SSH) :**
```bash
curl -fsSL https://raw.githubusercontent.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo/main/setup/create-template.sh -o /root/create-template.sh
bash /root/create-template.sh
```

**Option B — Via l'API Proxmox (depuis le PC local) :**
Le script `setup-ansible.py` s'en charge automatiquement si le template n'existe pas.

**Résultat** : Template `ubuntu-k3s-template` (ID 9000) visible dans Proxmox.

---

## Étape 7 : Lancer Terraform

```powershell
cd C:\Users\PC-HUGO\MSPR\terraform
terraform init
terraform plan       # Vérifier ce qui va être créé
terraform apply      # Confirmer avec "yes"
```

**Provider** : `bpg/proxmox` (le provider `telmate/proxmox` a des bugs de permissions).

**Durée** : ~2 minutes. Les 4 VMs sont créées + l'inventaire Ansible est auto-généré.

| VM | IP | Rôle |
|---|---|---|
| k3s-server (200) | 10.10.10.10 | Control-plane K3s |
| k3s-worker-1 (201) | 10.10.10.11 | Worker K3s |
| k3s-worker-2 (202) | 10.10.10.12 | Worker K3s |
| nfs-server (203) | 10.10.10.13 | Stockage NFS |

---

## Étape 8 : Lancer Ansible

Ansible est exécuté **depuis le serveur Proxmox** (car les VMs sont sur le réseau interne).

```bash
ssh root@<IP-SERVEUR-OVH>

# Cloner le repo
git clone https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo.git
cd MSPR1-Deploy-Odoo/ansible

# Installer Ansible et dépendances
apt-get install -y ansible python3-pip
pip3 install kubernetes PyYAML jsonpatch
ansible-galaxy collection install -r requirements.yml

# Générer une clé SSH locale pour accéder aux VMs
ssh-keygen -t ed25519 -f /root/.ssh/id_ansible -N ''

# Ajouter la clé aux VMs (via cloud-init + reboot)
# Voir setup/setup-ansible.py pour l'automatisation

# Créer l'inventaire local
mkdir -p inventory
# Copier le contenu de ansible/inventory/hosts.yml
# en remplaçant ansible_ssh_private_key_file par /root/.ssh/id_ansible

# Créer les symlinks group_vars
ln -sf ../group_vars inventory/group_vars
ln -sf ../group_vars playbooks/group_vars

# Lancer le déploiement complet
ansible-playbook playbooks/site.yml -v

# Initialiser la base Odoo (première fois seulement)
ssh -i /root/.ssh/id_ansible ubuntu@10.10.10.10 \
  'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml; \
   kubectl exec -n odoo deployment/odoo -- odoo -d odoo -i base --stop-after-init \
   --db_host=postgres --db_user=odoo --db_password=Ch4ng3M3!Pg2026; \
   kubectl rollout restart deployment/odoo -n odoo'
```

**Durée** : ~5 minutes. Le cluster K3s (3 noeuds) + NFS + cert-manager + Odoo sont déployés.

---

## Étape 9 : Port-forwarding + accéder à Odoo

### Sur le serveur Proxmox :
```bash
# Rediriger les ports vers le control-plane
iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 443 -j DNAT --to-destination 10.10.10.10:443
iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to-destination 10.10.10.10:80

# Rendre persistant
apt-get install -y iptables-persistent
netfilter-persistent save
```

### Sur ton PC Windows :

Ajoute dans `C:\Windows\System32\drivers\etc\hosts` (en admin) :
```
51.77.216.79  odoo.local
```

### Accéder à Odoo :

Ouvre **https://odoo.local** dans ton navigateur.
Accepte le certificat auto-signé.

---

## Vérification du cluster

```bash
ssh -i /root/.ssh/id_ansible ubuntu@10.10.10.10
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl get nodes          # 3 noeuds Ready
kubectl get pods -A        # Tous les pods Running
kubectl get pods -n odoo   # Odoo + PostgreSQL Running
kubectl get ingress -n odoo # Ingress actif sur odoo.local
```

---

## Résumé des durées

| Étape | Action | Durée |
|-------|--------|-------|
| 0 | Installation outils | ~10 min |
| 1-4 | Configuration Proxmox + réseau + SSH | ~20 min |
| 5 | Remplir tfvars | ~5 min |
| 6 | Créer template VM | ~5 min |
| 7 | Terraform apply | ~2 min |
| 8 | Ansible (K3s + Odoo) | ~5 min |
| 9 | Port-forwarding + test | ~5 min |
| **Total** | | **~50 min** |

---

## Architecture déployée

```
Internet
    │
    ▼
┌─────────────────────────────────────────┐
│  Proxmox (51.77.216.79)                 │
│  vmbr0 (public) ─── NAT ─── vmbr1      │
│                              (10.10.10.1)│
│  ┌──────────────────────────────────┐   │
│  │ k3s-server (10.10.10.10)        │   │
│  │  ├── Traefik (Ingress)          │   │
│  │  ├── cert-manager               │   │
│  │  └── PostgreSQL                 │   │
│  ├──────────────────────────────────┤   │
│  │ k3s-worker-1 (10.10.10.11)      │   │
│  │  └── Odoo                       │   │
│  ├──────────────────────────────────┤   │
│  │ k3s-worker-2 (10.10.10.12)      │   │
│  │  └── (réserve)                  │   │
│  ├──────────────────────────────────┤   │
│  │ nfs-server (10.10.10.13)        │   │
│  │  └── /srv/nfs/k8s (PV)         │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```
