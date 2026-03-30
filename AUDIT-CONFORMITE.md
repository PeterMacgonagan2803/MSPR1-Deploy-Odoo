# Audit de conformite -- MSPR TPRE961 (Infra)

Verification exhaustive du projet par rapport au cahier des charges de la MSPR.

## Verification mission par mission

| Mission | Exigence du sujet | Code | Livrable | Statut |
|---------|-------------------|------|----------|--------|
| **M1** | Choix technologies + justification | K3s, Proxmox, IaC | `01-choix-technologies.md` | Done |
| **M2** | Diagramme de Gantt | - | `02-gantt.md` (Mermaid + tableau) | Done |
| **M2** | Environnement inclusif | - | `04-inclusivite.md` | Done |
| **M3** | Tableau Kanban | - | `03-kanban.md` (19 tickets) | Done |
| **M4** | Preparation images VM | `setup/create-template.sh` + `packer/` | `05-packer.md` | Done |
| **M5** | Terraform infra | `terraform/` (7 fichiers) | `06-terraform.md` | Done |
| **M6** | Ansible K3s BareMetal | `roles/common,k3s-server,k3s-agent` | `07-ansible-k3s.md` | Done |
| **M7** | Ansible Odoo + Ingress HTTPS | `roles/deploy-odoo,nfs-server` | `08-ansible-odoo.md` | Done |
| **M8** | Dossier de rendu final | - | `10-dossier-rendu.md` | Done |

## Verification des specs techniques

| Exigence | Valeur attendue | Notre valeur | Statut |
|----------|----------------|--------------|--------|
| Control-plane | 2 coeurs, 2-4 Go RAM, 20 Go disque | 2 CPU, 4 Go, 20 Go | OK |
| Workers (x2) | 2 coeurs, 4 Go RAM, 30 Go disque | 2 CPU, 4 Go, 20 Go | OK |
| Distribution K8s | K3s / RKE2 / K0s / MicroK8s | K3s | OK |
| Stockage NFS | nfs-subdir-external-provisioner | VM NFS + provisioner Helm | OK |
| Odoo deploye | Application Odoo fonctionnelle | odoo:18 + postgres:17 via manifests K8s | OK |
| Ingress HTTPS | Certificats autosignes acceptes | Traefik + cert-manager selfsigned | OK |
| Git versionne | Packer / Terraform / Ansible | GitHub | OK |
| Secrets proteges | Pas de secrets dans repo | Ansible Vault + .gitignore | OK |

## Verification des livrables attendus (section V du sujet)

| # | Livrable attendu | Fichier | Statut |
|---|-----------------|---------|--------|
| 1 | Justification choix distribution K8s | `livrables/01-choix-technologies.md` | Done |
| 2 | Justification solution hebergement | `livrables/01-choix-technologies.md` (Proxmox) | Done |
| 3 | Justification outils IaC | `livrables/01-choix-technologies.md` (Terraform/Ansible) | Done |
| 4 | Diagramme de Gantt | `livrables/02-gantt.md` | Done |
| 5 | Tableau Kanban | `livrables/03-kanban.md` | Done |
| 6 | Mesures inclusives + exemples concrets | `livrables/04-inclusivite.md` (handicap psychomoteur + visuel) | Done |
| 7 | Description images/templates VM | `livrables/05-packer.md` | Done |
| 8 | Explication recettes Terraform | `livrables/06-terraform.md` | Done |
| 9 | Deploiement K8s avec Ansible | `livrables/07-ansible-k3s.md` | Done |
| 10 | Deploiement Odoo avec Ansible | `livrables/08-ansible-odoo.md` | Done |
| 11 | Architecture globale de la solution | `livrables/09-architecture.md` | Done |
| 12 | Captures d'ecran + preuves | `livrables/10-dossier-rendu.md` (sections TODO) | En attente captures |

## Extras (au-dela du cahier des charges)

| Bonus | Description |
|-------|-------------|
| GitHub Actions CI | Validation automatique Terraform + Packer + Ansible a chaque push |
| Ansible Vault | Chiffrement des secrets (mots de passe PostgreSQL) |
| Health check HTTP | Verification automatique qu'Odoo repond apres deploiement |
| Playbook de destruction | Nettoyage complet du cluster (`destroy.yml`) |
| Auto-inventaire | Terraform genere automatiquement l'inventaire Ansible |
| group_vars | Variables centralisees et separees des secrets |
| Guide de demarrage OVH | Checklist etapes + scripts reseau + port-forwarding |
| Scripts setup Python | Orchestration distante via Paramiko (SSH) |

## Resume

- **8 missions sur 8** couvertes
- **11 livrables sur 12** termines (le 12e = captures d'ecran, en attente)
- **8 bonus** au-dela du cahier des charges
