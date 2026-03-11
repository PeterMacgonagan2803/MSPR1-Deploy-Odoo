# Audit de conformité — MSPR TPRE961 (Infra)

Vérification exhaustive du projet par rapport au cahier des charges de la MSPR.

## Vérification mission par mission

| Mission | Exigence du sujet | Code | Livrable | Statut |
|---------|-------------------|------|----------|--------|
| **M1** | Choix technologies + justification | K3s, Proxmox, IaC | `01-choix-technologies.md` | ✅ Fait |
| **M2** | Diagramme de Gantt | - | `02-gantt.md` (Mermaid + tableau) | ✅ Fait |
| **M2** | Environnement inclusif | - | `04-inclusivite.md` | ✅ Fait |
| **M3** | Tableau Kanban | - | `03-kanban.md` (19 tickets) | ✅ Fait |
| **M4** | Packer images | `packer/` (4 fichiers) | `05-packer.md` | ✅ Fait |
| **M5** | Terraform infra | `terraform/` (7 fichiers) | `06-terraform.md` | ✅ Fait |
| **M6** | Ansible K3s BareMetal | `roles/common,k3s-server,k3s-agent` | `07-ansible-k3s.md` | ✅ Fait |
| **M7** | Ansible Odoo + Ingress HTTPS | `roles/deploy-odoo,nfs-server` | `08-ansible-odoo.md` | ✅ Fait |
| **M8** | Dossier de rendu final | - | `10-dossier-rendu.md` | ✅ Fait |

## Vérification des specs techniques

| Exigence | Valeur attendue | Notre valeur | Statut |
|----------|----------------|--------------|--------|
| Control-plane | 2 cœurs, 2-4 Go RAM, 20 Go disque | 2 CPU, 4 Go, 20 Go | ✅ |
| Workers (x2) | 2 cœurs, 4 Go RAM, 30 Go disque | 2 CPU, 4 Go, 30 Go | ✅ |
| Distribution K8s | K3s / RKE2 / K0s / MicroK8s | K3s | ✅ |
| Stockage NFS | nfs-subdir-external-provisioner | VM NFS + provisioner Helm | ✅ |
| Odoo via Helm | kubernetes.core.helm + bitnami | bitnami/odoo via Helm | ✅ |
| Ingress HTTPS | Certificats autosignés acceptés | Traefik + cert-manager selfsigned | ✅ |
| Git versionné | Packer / Terraform / Ansible | GitHub public | ✅ |
| Secrets protégés | Pas de secrets dans repo public | Ansible Vault + .gitignore | ✅ |

## Vérification des livrables attendus (section V du sujet)

| # | Livrable attendu | Fichier | Statut |
|---|-----------------|---------|--------|
| 1 | Justification choix distribution K8s | `livrables/01-choix-technologies.md` | ✅ Fait |
| 2 | Justification solution hébergement | `livrables/01-choix-technologies.md` (Proxmox) | ✅ Fait |
| 3 | Justification outils IaC | `livrables/01-choix-technologies.md` (Packer/TF/Ansible) | ✅ Fait |
| 4 | Diagramme de Gantt | `livrables/02-gantt.md` | ✅ Fait |
| 5 | Tableau Kanban | `livrables/03-kanban.md` | ✅ Fait |
| 6 | Mesures inclusives + exemples concrets | `livrables/04-inclusivite.md` (handicap psychomoteur + visuel) | ✅ Fait |
| 7 | Description images Packer | `livrables/05-packer.md` | ✅ Fait |
| 8 | Explication recettes Terraform | `livrables/06-terraform.md` | ✅ Fait |
| 9 | Déploiement K8s avec Ansible | `livrables/07-ansible-k3s.md` | ✅ Fait |
| 10 | Déploiement Odoo avec Ansible | `livrables/08-ansible-odoo.md` | ✅ Fait |
| 11 | Architecture globale de la solution | `livrables/09-architecture.md` | ✅ Fait |
| 12 | Captures d'écran + preuves | `livrables/10-dossier-rendu.md` (sections TODO) | ⏳ Après déploiement |

## Éléments restants (nécessitent l'infrastructure réelle)

| Élément | Quand | Comment |
|---------|-------|---------|
| **Captures d'écran** | Après déploiement sur OVH | Compléter les sections 11.1 à 11.7 dans `10-dossier-rendu.md` |
| **Difficultés rencontrées** | Pendant le projet | Compléter la section 12 dans `10-dossier-rendu.md` |
| **Support de soutenance** | Avant la soutenance | PowerPoint / Slides (20 min de présentation) |
| **Démo live** | Jour de la soutenance | Cluster fonctionnel + montrer Odoo en HTTPS |

## Extras (au-delà du cahier des charges)

| Bonus | Description |
|-------|-------------|
| ✅ GitHub Actions CI | Validation automatique Terraform + Packer + Ansible à chaque push |
| ✅ Ansible Vault | Chiffrement des secrets (mots de passe Odoo/PostgreSQL) |
| ✅ Health check HTTP | Vérification automatique qu'Odoo répond après déploiement |
| ✅ Playbook de destruction | Nettoyage complet du cluster (`destroy.yml`) |
| ✅ Auto-inventaire | Terraform génère automatiquement l'inventaire Ansible |
| ✅ group_vars | Variables centralisées et séparées des secrets |
| ✅ Guide de démarrage OVH | Checklist 10 étapes + scripts réseau + port-forwarding |

## Résumé

- **44 fichiers** dans le projet
- **8 missions sur 8** couvertes
- **11 livrables sur 12** terminés (le 12ᵉ = captures d'écran, après déploiement)
- **7 bonus** au-delà du cahier des charges
