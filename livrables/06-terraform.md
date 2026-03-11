# Mission 5 : Terraform — Préparation et déploiement de l'infrastructure

## 1. Objectif

Déployer automatiquement les 4 machines virtuelles nécessaires au cluster K3s sur Proxmox, à partir du template créé par Packer, et générer l'inventaire Ansible correspondant.

## 2. Structure des fichiers

```
terraform/
├── providers.tf              # Configuration du provider Proxmox
├── variables.tf              # Définition de toutes les variables
├── main.tf                   # Ressources principales (VMs)
├── inventory.tf              # Génération automatique de l'inventaire Ansible
├── outputs.tf                # Sorties (IPs, infos VMs)
├── terraform.tfvars.example  # Exemple de configuration (à copier/adapter)
└── templates/
    └── hosts.yml.tftpl       # Template pour l'inventaire Ansible
```

## 3. Provider Proxmox

Le provider `telmate/proxmox` (version >= 3.0.1) permet à Terraform de communiquer avec l'API Proxmox pour créer, modifier et supprimer des VMs.

```hcl
provider "proxmox" {
  pm_api_url          = var.proxmox_url
  pm_api_token_id     = var.proxmox_token_id
  pm_api_token_secret = var.proxmox_token_secret
  pm_tls_insecure     = true
}
```

L'authentification se fait via **API Token** (plus sécurisé qu'un mot de passe) :
1. Créer un token dans Proxmox : Datacenter → Permissions → API Tokens
2. Renseigner le `token_id` et `token_secret` dans `terraform.tfvars`

## 4. Ressources déployées

### VMs provisionnées via `for_each`

Terraform utilise une boucle `for_each` sur une map `locals` pour déployer les 4 VMs en une seule ressource :

| VM | VMID | CPU | RAM | Disque | Rôle |
|----|------|-----|-----|--------|------|
| `k3s-server` | 200 | 2 coeurs | 4 Go | 20 Go | Control-plane K3s |
| `k3s-worker-1` | 201 | 2 coeurs | 4 Go | 30 Go | Worker K3s |
| `k3s-worker-2` | 202 | 2 coeurs | 4 Go | 30 Go | Worker K3s |
| `nfs-server` | 203 | 1 coeur | 1 Go | 50 Go | Serveur NFS |

Ces specs respectent les exigences minimales du cahier des charges :
- Control-plane : 2 coeurs, 4 Go RAM (recommandé), 20 Go disque
- Workers : 2 coeurs, 4 Go RAM (recommandé), 30 Go disque

### Configuration réseau

Chaque VM reçoit :
- Une **IP statique** configurée via cloud-init (`ipconfig0`)
- Un accès au **gateway** réseau
- Un serveur **DNS** (configurable, par défaut `8.8.8.8`)
- Une **clé SSH publique** pour l'accès sans mot de passe

## 5. Génération automatique de l'inventaire Ansible

L'un des points forts de notre infrastructure : Terraform génère automatiquement le fichier `ansible/inventory/hosts.yml` après le déploiement des VMs. Plus besoin de copier manuellement les IPs.

Le fichier `inventory.tf` utilise `templatefile()` pour remplir le template `hosts.yml.tftpl` avec les IPs réelles des VMs déployées.

**Avantage** : Un seul `terraform apply` crée les VMs ET prépare l'inventaire Ansible. Zéro intervention manuelle entre les deux étapes.

## 6. Outputs

Après `terraform apply`, les sorties affichent :

```
control_plane_ip = "10.0.0.10"
worker_1_ip      = "10.0.0.11"
worker_2_ip      = "10.0.0.12"
nfs_server_ip    = "10.0.0.13"
```

## 7. Variables paramétrables

| Variable | Description | Défaut |
|----------|-------------|--------|
| `proxmox_url` | URL API Proxmox | (requis) |
| `proxmox_token_id` | Token ID API | (requis) |
| `proxmox_token_secret` | Token secret API | (requis, sensible) |
| `proxmox_node` | Noeud Proxmox cible | (requis) |
| `template_name` | Nom du template Packer | `ubuntu-k3s-template` |
| `ip_control_plane` | IP du control-plane (CIDR) | (requis) |
| `ip_worker_1` | IP du worker 1 (CIDR) | (requis) |
| `ip_worker_2` | IP du worker 2 (CIDR) | (requis) |
| `ip_nfs` | IP du serveur NFS (CIDR) | (requis) |
| `gateway` | Passerelle réseau | (requis) |
| `k3s_version` | Version K3s | `v1.29.2+k3s1` |
| `odoo_domain` | Domaine Odoo | `odoo.local` |

## 8. Commandes d'utilisation

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars  # Copier et adapter
terraform init                                 # Initialiser les providers
terraform plan                                 # Prévisualiser les changements
terraform apply                                # Déployer l'infrastructure
terraform destroy                              # Supprimer l'infrastructure
```

## 9. Gestion de l'état (tfstate)

Le fichier `terraform.tfstate` contient l'état de l'infrastructure déployée. Il est exclu du dépôt Git (`.gitignore`) car il peut contenir des informations sensibles. En production, il serait stocké dans un backend distant (S3, Consul, etc.).

## 10. Intérêt pour le PRA

`terraform apply` recrée l'ensemble des 4 VMs en **~5 minutes**, avec les IPs identiques et la configuration réseau complète. Combiné avec le template Packer, aucune intervention manuelle n'est nécessaire pour reconstituer l'infrastructure.
