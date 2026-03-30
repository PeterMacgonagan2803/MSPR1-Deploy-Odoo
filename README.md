# MSPR1-Deploy-Odoo

[![CI - Validation IaC](https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo/actions/workflows/ci.yml/badge.svg)](https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo/actions/workflows/ci.yml)

Projet MSPR TPRE961 - Infrastructure virtualisee pour le deploiement de l'ERP Odoo sur un cluster Kubernetes (K3s), automatise via Terraform et Ansible, sur Proxmox VE.

## Architecture

```
+-------------------------------------------------------------+
|                    Proxmox VE (OVH Dedie)                    |
|                    IP publique : x.x.x.x                     |
|                                                              |
|  NAT iptables :80/:443 --> 10.10.10.10                       |
|                                                              |
|  +--------------+  +--------------+  +--------------+        |
|  | k3s-server   |  | k3s-worker-1 |  | k3s-worker-2 |        |
|  | (ctrl-plane) |  |              |  |              |        |
|  | 2 CPU / 4 Go |  | 2 CPU / 4 Go |  | 2 CPU / 4 Go |        |
|  | 10.10.10.10  |  | 10.10.10.11  |  | 10.10.10.12  |        |
|  +------+-------+  +------+-------+  +------+-------+        |
|         |                 |                 |                 |
|         +--------+--------+---------+-------+                 |
|                  |   K3s Cluster     |                        |
|                  |  +------------+   |                        |
|                  |  |  Traefik   |   |                        |
|                  |  | (Ingress)  |   |                        |
|                  |  +-----+------+   |                        |
|                  |        |          |                        |
|                  |  +-----+------+   |                        |
|                  |  | Odoo :18   |   |                        |
|                  |  | PG   :17   |   |                        |
|                  |  +------------+   |                        |
|                  |                   |                        |
|  +--------------+                                            |
|  |  nfs-server  |<-- Stockage persistant (PV/PVC)            |
|  | 1 CPU / 1 Go |                                            |
|  | 10.10.10.13  |                                            |
|  +--------------+                                            |
+--------------------------------------------------------------+
```

## Prerequis

- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/) >= 2.15
- [Helm](https://helm.sh/docs/intro/install/) >= 3.12
- Acces a un serveur Proxmox VE avec credentials API
- Python 3 + Paramiko (pour les scripts de setup distants)

## Technologies

| Outil | Role |
|-------|------|
| **Proxmox VE** | Hyperviseur bare-metal |
| **Cloud-init** | Template VM Ubuntu 22.04 standardise |
| **Terraform** (`bpg/proxmox`) | Provisionnement des VMs (IaC) + inventaire Ansible auto |
| **Ansible** | Configuration du cluster K3s + deploiement Odoo |
| **K3s** | Distribution Kubernetes legere (Traefik + ServiceLB integres) |
| **Helm** | NFS Provisioner + cert-manager |
| **Manifests K8s** | Odoo 18 + PostgreSQL 17 (images officielles) |
| **NFS** | Stockage persistant pour les PV Kubernetes |
| **cert-manager** | Certificats TLS (autosignes pour le PoC) |
| **GitHub Actions** | CI - Validation automatique IaC |

## Deploiement rapide

### 1. Creer le template VM sur Proxmox

```bash
# Sur le serveur Proxmox (SSH root)
bash setup/create-template.sh
```

### 2. Deployer l'infrastructure avec Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Editer terraform.tfvars avec vos parametres Proxmox
terraform init
terraform plan
terraform apply
```

### 3. Configurer le cluster et deployer Odoo avec Ansible

```bash
cd ansible
ansible-galaxy collection install -r requirements.yml

# Chiffrer les secrets (premiere fois uniquement)
ansible-vault encrypt group_vars/all/vault.yml

# Lancer le deploiement complet
ansible-playbook playbooks/site.yml --ask-vault-pass
```

### 4. Acceder a Odoo

Ajouter dans le fichier `hosts` :
```
<IP_PUBLIQUE_PROXMOX>  odoo.local
```

Puis ouvrir http://odoo.local (login: `admin` / password: `admin`).

### 5. Destruction (nettoyage)

```bash
cd ansible
ansible-playbook playbooks/destroy.yml --ask-vault-pass
cd ../terraform
terraform destroy
```

> Pour un guide detaille pas-a-pas avec un serveur OVH, voir [`setup/GUIDE-DEMARRAGE.md`](setup/GUIDE-DEMARRAGE.md).

## Gestion des secrets

Les mots de passe sont stockes dans `ansible/group_vars/all/vault.yml`, a chiffrer via **Ansible Vault** :

```bash
ansible-vault encrypt ansible/group_vars/all/vault.yml
ansible-vault edit ansible/group_vars/all/vault.yml
ansible-playbook playbooks/site.yml --ask-vault-pass
```

## Structure du projet

```
.
+-- .github/workflows/ci.yml    # CI GitHub Actions
+-- setup/                       # Scripts de deploiement OVH/Proxmox
|   +-- GUIDE-DEMARRAGE.md      # Guide pas-a-pas complet
|   +-- create-template.sh      # Creation du template VM cloud-init
|   +-- configure-network.sh    # Configuration reseau NAT Proxmox
|   +-- install-tools.ps1       # Installation des outils (Windows)
|   +-- setup-ansible.py        # Orchestration Ansible distante
|   +-- port-forward-odoo.sh    # Port-forwarding iptables
|   +-- init-odoo.py            # Initialisation base Odoo
|   +-- remote-exec.py          # Execution SSH distante (Paramiko)
|   +-- remote-bg.py            # Execution background (screen)
+-- terraform/                   # Infrastructure (Terraform)
|   +-- providers.tf             # Provider bpg/proxmox
|   +-- main.tf                  # Ressources VMs (for_each)
|   +-- variables.tf             # Variables
|   +-- outputs.tf               # Sorties (IPs)
|   +-- inventory.tf             # Generation auto inventaire Ansible
|   +-- terraform.tfvars.example # Exemple de configuration
|   +-- templates/hosts.yml.tftpl
+-- ansible/                     # Configuration & Deploiement
|   +-- ansible.cfg              # Configuration Ansible
|   +-- requirements.yml         # Collections Galaxy
|   +-- group_vars/all/
|   |   +-- vars.yml             # Variables publiques
|   |   +-- vault.yml            # Secrets (Ansible Vault)
|   |   +-- vault.yml.example    # Exemple de vault
|   +-- inventory/               # Inventaire (auto-genere par Terraform)
|   +-- playbooks/
|   |   +-- site.yml             # Deploiement complet
|   |   +-- k3s-cluster.yml      # Cluster K3s uniquement
|   |   +-- deploy-odoo.yml      # Odoo uniquement
|   |   +-- destroy.yml          # Nettoyage complet
|   +-- roles/
|       +-- common/              # Configuration de base des VMs
|       +-- k3s-server/          # Installation K3s control-plane
|       +-- k3s-agent/           # Installation K3s workers
|       +-- nfs-server/          # Configuration serveur NFS
|       +-- deploy-odoo/         # Deploiement Odoo + PostgreSQL + cert-manager
+-- packer/                      # Approche alternative (reference)
+-- livrables/                   # Documentation detaillee par mission
+-- AUDIT-CONFORMITE.md          # Verification conformite cahier des charges
+-- README.md
```

## Livrables

| # | Document | Description |
|---|----------|-------------|
| 1 | [Choix technologies](livrables/01-choix-technologies.md) | Justification K3s, Proxmox, IaC |
| 2 | [Gantt](livrables/02-gantt.md) | Planning previsionnel (19h) |
| 3 | [Kanban](livrables/03-kanban.md) | Suivi agile (19 tickets) |
| 4 | [Inclusivite](livrables/04-inclusivite.md) | Mesures handicap, diversite |
| 5 | [Template VM](livrables/05-packer.md) | Preparation des images |
| 6 | [Terraform](livrables/06-terraform.md) | Infrastructure as Code |
| 7 | [Ansible K3s](livrables/07-ansible-k3s.md) | Deploiement cluster |
| 8 | [Ansible Odoo](livrables/08-ansible-odoo.md) | Deploiement applicatif |
| 9 | [Architecture](livrables/09-architecture.md) | Schema global |
| 10 | [Dossier rendu](livrables/10-dossier-rendu.md) | Document final complet |

## Equipe

- PeterMacgonagan2803
- AugustinBeeuwsaert
