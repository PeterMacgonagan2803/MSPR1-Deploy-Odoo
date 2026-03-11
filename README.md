# MSPR1-Deploy-Odoo

[![CI - Validation IaC](https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo/actions/workflows/ci.yml/badge.svg)](https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo/actions/workflows/ci.yml)

Projet MSPR TPRE961 - Infrastructure virtualisée pour le déploiement de l'ERP Odoo sur un cluster Kubernetes (K3s), automatisé via Packer, Terraform et Ansible.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Proxmox VE                           │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ k3s-server   │  │ k3s-worker-1 │  │ k3s-worker-2 │  │
│  │ (ctrl-plane) │  │              │  │              │  │
│  │ 2 CPU / 4 Go │  │ 2 CPU / 4 Go │  │ 2 CPU / 4 Go │  │
│  │ 20 Go disk   │  │ 30 Go disk   │  │ 30 Go disk   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │           │
│         └────────┬────────┴────────┬────────┘           │
│                  │   K3s Cluster   │                    │
│                  │  ┌───────────┐  │                    │
│                  │  │  Traefik  │  │                    │
│                  │  │ (Ingress) │  │                    │
│                  │  └─────┬─────┘  │                    │
│                  │        │        │                    │
│                  │  ┌─────┴─────┐  │                    │
│                  │  │   Odoo    │  │                    │
│                  │  │ (Helm)    │  │                    │
│                  │  └───────────┘  │                    │
│                  │                 │                    │
│  ┌──────────────┐                                      │
│  │  nfs-server  │◄── Stockage persistant (PV/PVC)      │
│  │ 1 CPU / 1 Go │                                      │
│  │ 50 Go disk   │                                      │
│  └──────────────┘                                      │
└─────────────────────────────────────────────────────────┘
```

## Prérequis

- [Packer](https://developer.hashicorp.com/packer/downloads) >= 1.9
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/) >= 2.15
- [Helm](https://helm.sh/docs/intro/install/) >= 3.12
- Accès à un serveur Proxmox VE avec les credentials API
- Une image ISO Ubuntu Server 22.04 LTS sur le Proxmox

## Technologies choisies

| Outil | Rôle |
|-------|------|
| **Proxmox VE** | Hyperviseur bare-metal |
| **Packer** | Création de templates VM Ubuntu |
| **Terraform** | Provisionnement des VMs (IaC) + génération auto de l'inventaire Ansible |
| **Ansible** | Configuration du cluster K3s + déploiement Odoo |
| **K3s** | Distribution Kubernetes légère (inclut Traefik + ServiceLB) |
| **Helm** | Gestionnaire de packages Kubernetes |
| **NFS** | Stockage persistant pour les PV Kubernetes |
| **cert-manager** | Gestion des certificats TLS (autosignés) |
| **GitHub Actions** | CI - Validation automatique (terraform validate, packer validate, ansible-lint) |

## Utilisation rapide

### 1. Préparer l'image avec Packer

```bash
cd packer
packer init .
packer build -var-file=variables.pkr.hcl .
```

### 2. Déployer l'infrastructure avec Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Éditer terraform.tfvars avec vos paramètres Proxmox
terraform init
terraform plan
terraform apply
# L'inventaire Ansible est généré automatiquement dans ansible/inventory/hosts.yml
```

### 3. Configurer le cluster et déployer Odoo avec Ansible

```bash
cd ansible
ansible-galaxy collection install -r requirements.yml

# Chiffrer les secrets (première fois uniquement)
ansible-vault encrypt group_vars/all/vault.yml

# Lancer le déploiement complet
ansible-playbook playbooks/site.yml --ask-vault-pass
```

### 4. Accéder à Odoo

Une fois le déploiement terminé, Odoo est accessible via :
```
https://odoo.local
```
(Ajouter l'entrée dans `/etc/hosts` pointant vers l'IP du control-plane ou du LoadBalancer)

### 5. Destruction (nettoyage)

```bash
cd ansible
ansible-playbook playbooks/destroy.yml --ask-vault-pass
cd ../terraform
terraform destroy
```

## Gestion des secrets

Les mots de passe sont stockés dans `ansible/group_vars/all/vault.yml` et chiffrés via **Ansible Vault**.

```bash
# Chiffrer
ansible-vault encrypt ansible/group_vars/all/vault.yml

# Éditer
ansible-vault edit ansible/group_vars/all/vault.yml

# Lancer avec le vault
ansible-playbook playbooks/site.yml --ask-vault-pass
# ou avec un fichier mot de passe
ansible-playbook playbooks/site.yml --vault-password-file .vault_pass
```

## Structure du projet

```
.
├── .github/workflows/ci.yml   # CI GitHub Actions
├── packer/                     # Images VM (Packer)
│   ├── ubuntu-k3s.pkr.hcl     # Template Packer principal
│   ├── variables.pkr.hcl      # Variables Packer
│   └── http/                   # Cloud-init autoinstall
├── terraform/                  # Infrastructure (Terraform)
│   ├── main.tf                 # Ressources principales (VMs)
│   ├── inventory.tf            # Génération auto inventaire Ansible
│   ├── variables.tf            # Définition des variables
│   ├── outputs.tf              # Sorties (IPs, etc.)
│   ├── providers.tf            # Configuration du provider Proxmox
│   └── templates/              # Templates pour l'inventaire
├── ansible/                    # Configuration & Déploiement (Ansible)
│   ├── ansible.cfg             # Configuration Ansible
│   ├── requirements.yml        # Collections Galaxy requises
│   ├── group_vars/all/         # Variables centralisées
│   │   ├── vars.yml            # Variables publiques
│   │   └── vault.yml           # Secrets (Ansible Vault)
│   ├── inventory/              # Inventaire (auto-généré par Terraform)
│   ├── playbooks/              # Playbooks principaux
│   │   ├── site.yml            # Déploiement complet
│   │   ├── k3s-cluster.yml     # Cluster K3s uniquement
│   │   ├── deploy-odoo.yml     # Odoo uniquement
│   │   └── destroy.yml         # Nettoyage complet
│   └── roles/
│       ├── common/             # Configuration de base des VMs
│       ├── k3s-server/         # Installation K3s control-plane
│       ├── k3s-agent/          # Installation K3s workers
│       ├── nfs-server/         # Configuration serveur NFS
│       └── deploy-odoo/        # Déploiement Odoo + dépendances
└── README.md
```

## Équipe

- PeterMacgonagan2803
- AugustinBeeuwsaert
