# Guide de démarrage — Serveur OVH + Proxmox

## Checklist complète (dans l'ordre)

- [ ] **Étape 0** — Installer les outils sur ton PC
- [ ] **Étape 1** — Premier accès à Proxmox et configuration de base
- [ ] **Étape 2** — Créer un API Token Proxmox (pour Terraform)
- [ ] **Étape 3** — Uploader l'ISO Ubuntu sur Proxmox
- [ ] **Étape 4** — Configurer le réseau Proxmox
- [ ] **Étape 5** — Générer ta paire de clés SSH
- [ ] **Étape 6** — Remplir les fichiers de configuration (tfvars, packer)
- [ ] **Étape 7** — Lancer Packer (créer le template VM)
- [ ] **Étape 8** — Lancer Terraform (déployer les 4 VMs)
- [ ] **Étape 9** — Lancer Ansible (cluster K3s + Odoo)
- [ ] **Étape 10** — Vérifier et accéder à Odoo

---

## Étape 0 : Installer les outils sur ton PC

Lance le script `install-tools.ps1` (en tant qu'admin) :

```powershell
cd setup
.\install-tools.ps1
```

Cela installe : Terraform, Packer, Ansible (via WSL/pip), Helm, kubectl.

**Vérification :**
```powershell
terraform --version
packer --version
ansible --version
helm version
kubectl version --client
```

---

## Étape 1 : Premier accès à Proxmox

1. Connecte-toi à l'interface web Proxmox :
   ```
   https://<IP-SERVEUR-OVH>:8006
   ```
2. Identifiants par défaut OVH : `root` + le mot de passe défini lors de la commande
3. Note ces informations :
   - **IP publique du serveur** : `_______________`
   - **Nom du noeud Proxmox** : (visible en haut à gauche, souvent `pve` ou le hostname)
   - **Pool de stockage** : (Datacenter → Storage, souvent `local-lvm`)

---

## Étape 2 : Créer un API Token Proxmox

L'API Token permet à Terraform de communiquer avec Proxmox **sans utiliser le mot de passe root**.

1. Dans Proxmox : **Datacenter → Permissions → API Tokens → Add**
2. Remplis :
   - User : `root@pam`
   - Token ID : `terraform`
   - **Décocher** "Privilege Separation" (sinon le token n'a pas les droits)
3. **COPIE le Token Secret** qui s'affiche (il ne sera plus jamais affiché !)
4. Note :
   - **Token ID** : `root@pam!terraform`
   - **Token Secret** : `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

---

## Étape 3 : Uploader l'ISO Ubuntu

1. Télécharge l'ISO Ubuntu 22.04.4 LTS Server :
   ```
   https://releases.ubuntu.com/22.04/ubuntu-22.04.4-live-server-amd64.iso
   ```
2. Dans Proxmox : **local (pve) → ISO Images → Upload**
3. Sélectionne l'ISO et upload
4. Note le nom exact du fichier (ex: `ubuntu-22.04.4-live-server-amd64.iso`)

**Alternative via SSH** (plus rapide) :
```bash
ssh root@<IP-SERVEUR-OVH>
cd /var/lib/vz/template/iso/
wget https://releases.ubuntu.com/22.04/ubuntu-22.04.4-live-server-amd64.iso
```

---

## Étape 4 : Configurer le réseau Proxmox

### Option A : IP publique unique OVH (le plus courant)

Si tu as une seule IP publique, il faut créer un réseau interne NAT pour les VMs.

1. SSH sur le serveur Proxmox :
   ```bash
   ssh root@<IP-SERVEUR-OVH>
   ```
2. Lance le script de configuration réseau :
   ```bash
   # Copie le contenu de setup/configure-network.sh sur le serveur et exécute-le
   ```

Les VMs auront des IPs en `10.10.10.x` et accèderont à internet via NAT.

### Option B : IPs failover OVH (ou bloc IP)

Si tu as des IPs failover, chaque VM peut avoir sa propre IP publique. Dans ce cas, utilise le bridge `vmbr0` directement avec les IPs failover.

---

## Étape 5 : Générer ta paire de clés SSH

```powershell
ssh-keygen -t ed25519 -C "mspr-cogip" -f $env:USERPROFILE\.ssh\id_mspr
```

- Clé privée : `~/.ssh/id_mspr`
- Clé publique : `~/.ssh/id_mspr.pub`

Affiche la clé publique (tu en auras besoin pour les tfvars) :
```powershell
Get-Content $env:USERPROFILE\.ssh\id_mspr.pub
```

---

## Étape 6 : Remplir les fichiers de configuration

### 6a. Terraform

```powershell
cd C:\Users\PC-HUGO\MSPR\terraform
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Remplis avec tes vraies valeurs (IP serveur, token, IPs réseau, clé SSH).

### 6b. Packer (optionnel, variables en ligne de commande possible)

Les variables Packer peuvent être passées via `-var` ou un fichier `.auto.pkrvars.hcl`.

---

## Étape 7 : Lancer Packer

```bash
cd C:\Users\PC-HUGO\MSPR\packer
packer init .
packer build \
  -var "proxmox_url=https://<IP>:8006/api2/json" \
  -var "proxmox_username=root@pam" \
  -var "proxmox_password=<MOT_DE_PASSE>" \
  -var "proxmox_node=<NOM_NOEUD>" \
  -var "iso_file=local:iso/ubuntu-22.04.4-live-server-amd64.iso" \
  -var "storage_pool=local-lvm" \
  .
```

**Durée** : ~15 minutes. À la fin, un template `ubuntu-k3s-template` apparaît dans Proxmox.

---

## Étape 8 : Lancer Terraform

```powershell
cd C:\Users\PC-HUGO\MSPR\terraform
terraform init
terraform plan       # Vérifier ce qui va être créé
terraform apply      # Confirmer avec "yes"
```

**Durée** : ~5 minutes. Les 4 VMs sont créées + l'inventaire Ansible est généré.

**Vérifie** que les VMs sont accessibles :
```powershell
ssh -i ~/.ssh/id_mspr ubuntu@10.10.10.10
ssh -i ~/.ssh/id_mspr ubuntu@10.10.10.11
ssh -i ~/.ssh/id_mspr ubuntu@10.10.10.12
ssh -i ~/.ssh/id_mspr ubuntu@10.10.10.13
```

---

## Étape 9 : Lancer Ansible

```bash
cd C:\Users\PC-HUGO\MSPR\ansible

# Installer les collections Ansible Galaxy
ansible-galaxy collection install -r requirements.yml

# Chiffrer les secrets (première fois)
ansible-vault encrypt group_vars/all/vault.yml

# Lancer le déploiement complet
ansible-playbook playbooks/site.yml --ask-vault-pass
```

**Durée** : ~15 minutes. Le cluster K3s + Odoo sont déployés.

---

## Étape 10 : Vérifier et accéder à Odoo

### Depuis le control-plane :
```bash
ssh -i ~/.ssh/id_mspr ubuntu@10.10.10.10
kubectl get nodes
kubectl get pods -A
kubectl get ingress -n odoo
```

### Accéder à Odoo dans le navigateur :

Ajoute dans `C:\Windows\System32\drivers\etc\hosts` :
```
<IP_CONTROL_PLANE>  odoo.local
```

Puis ouvre : **https://odoo.local**

- Email : `admin@cogip.local`
- Mot de passe : celui défini dans le vault

---

## Résumé des durées

| Étape | Action | Durée |
|-------|--------|-------|
| 0 | Installation outils | ~10 min |
| 1-5 | Configuration Proxmox + réseau + SSH | ~30 min |
| 6 | Remplir tfvars | ~5 min |
| 7 | Packer build | ~15 min |
| 8 | Terraform apply | ~5 min |
| 9 | Ansible playbook | ~15 min |
| 10 | Vérification | ~5 min |
| **Total** | | **~1h30** |
