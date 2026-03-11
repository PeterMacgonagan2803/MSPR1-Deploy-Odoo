# MSPR1-Deploy-Odoo

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
| **Terraform** | Provisionnement des VMs (IaC) |
| **Ansible** | Configuration du cluster K3s + déploiement Odoo |
| **K3s** | Distribution Kubernetes légère (inclut Traefik + ServiceLB) |
| **Helm** | Gestionnaire de packages Kubernetes |
| **NFS** | Stockage persistant pour les PV Kubernetes |
| **cert-manager** | Gestion des certificats TLS (autosignés) |

## Utilisation rapide

### 1. Préparer l'image avec Packer

```bash
cd packer
cp variables.pkr.hcl.example variables.pkr.hcl
# Éditer variables.pkr.hcl avec vos paramètres Proxmox
packer init .
packer build .
```

### 2. Déployer l'infrastructure avec Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Éditer terraform.tfvars avec vos paramètres
terraform init
terraform plan
terraform apply
```

### 3. Configurer le cluster et déployer Odoo avec Ansible

```bash
cd ansible
# Installer les collections Ansible requises
ansible-galaxy install -r requirements.yml
# Éditer l'inventaire avec les IPs des VMs
cp inventory/hosts.yml.example inventory/hosts.yml
# Lancer le déploiement complet
ansible-playbook playbooks/site.yml
```

### 4. Accéder à Odoo

Une fois le déploiement terminé, Odoo est accessible via :
```
https://odoo.local
```
(Ajouter l'entrée dans `/etc/hosts` pointant vers l'IP du control-plane ou du LoadBalancer)

## Structure du projet

```
.
├── packer/                  # Images VM (Packer)
│   ├── ubuntu-k3s.pkr.hcl  # Template Packer principal
│   ├── variables.pkr.hcl   # Variables Packer
│   └── http/                # Cloud-init autoinstall
├── terraform/               # Infrastructure (Terraform)
│   ├── main.tf              # Ressources principales
│   ├── variables.tf         # Définition des variables
│   ├── outputs.tf           # Sorties (IPs, etc.)
│   └── providers.tf         # Configuration du provider Proxmox
├── ansible/                 # Configuration & Déploiement (Ansible)
│   ├── ansible.cfg          # Configuration Ansible
│   ├── requirements.yml     # Collections Galaxy requises
│   ├── inventory/           # Inventaire des hôtes
│   ├── playbooks/           # Playbooks principaux
│   └── roles/               # Rôles Ansible
│       ├── common/          # Configuration de base des VMs
│       ├── k3s-server/      # Installation K3s control-plane
│       ├── k3s-agent/       # Installation K3s workers
│       ├── nfs-server/      # Configuration serveur NFS
│       └── deploy-odoo/     # Déploiement Odoo + dépendances
└── README.md
```

## Équipe

- PeterMacgonagan2803
- AugustinBeeuwsaert
