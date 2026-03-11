# Mission 8 : Dossier de rendu final — MSPR COGIP

## Sommaire

1. [Introduction et contexte](#1-introduction-et-contexte)
2. [Choix des technologies](#2-choix-des-technologies)
3. [Organisation du projet](#3-organisation-du-projet)
4. [Suivi de l'avancement](#4-suivi-de-lavancement)
5. [Mesures d'inclusivité](#5-mesures-dinclusivité)
6. [Packer — Préparation des images](#6-packer)
7. [Terraform — Déploiement de l'infrastructure](#7-terraform)
8. [Ansible — Déploiement de Kubernetes](#8-ansible-k3s)
9. [Ansible — Déploiement d'Odoo](#9-ansible-odoo)
10. [Architecture globale](#10-architecture-globale)
11. [Captures d'écran et preuves](#11-captures-décran)
12. [Difficultés rencontrées et solutions](#12-difficultés-et-solutions)
13. [Conclusion](#13-conclusion)
14. [Annexes](#14-annexes)

---

## 1. Introduction et contexte

La société COGIP, spécialisée dans les ERP, a décroché un contrat avec le groupe Tesker (véhicules électriques). Notre entreprise a remporté l'appel d'offres pour la mise en place d'une infrastructure hébergeant l'ERP Odoo, répondant aux critères suivants :
- **Évolutivité** : capacité de dimensionnement facile
- **Performance** : ressources adaptées à Odoo
- **Résilience** : résistance aux pannes
- **Reproductibilité** : Infrastructure as Code pour le PRA

La solution proposée : un cluster **Kubernetes K3s** déployé via **Packer + Terraform + Ansible** sur **Proxmox VE**.

## 2. Choix des technologies

> Détail complet : voir [01-choix-technologies.md](./01-choix-technologies.md)

**Résumé** :
- **K3s** : Distribution K8s légère, certifiée CNCF, avec LoadBalancer et Ingress Traefik intégrés
- **Proxmox VE** : Hyperviseur open-source avec API REST complète
- **Packer** : Templates VM reproductibles
- **Terraform** : Provisionnement déclaratif de l'infrastructure
- **Ansible** : Configuration agentless et déploiement applicatif via Helm
- **NFS** : Stockage persistant léger pour le PoC
- **cert-manager** : Certificats TLS automatiques (autosignés pour le PoC)

## 3. Organisation du projet

> Détail complet : voir [02-gantt.md](./02-gantt.md)

Le projet a été découpé en **15 tâches** réparties sur les 19 heures de préparation. Un diagramme de Gantt (format Mermaid) détaille le planning prévisionnel et les dépendances entre tâches.

## 4. Suivi de l'avancement

> Détail complet : voir [03-kanban.md](./03-kanban.md)

Un tableau Kanban à 4 colonnes (A faire → En cours → Revue Technique → Terminé) a été utilisé pour suivre les 19 tickets du projet. La revue technique a été réalisée collectivement.

## 5. Mesures d'inclusivité

> Détail complet : voir [04-inclusivite.md](./04-inclusivite.md)

Des mesures concrètes ont été définies pour :
- L'accueil de personnes en situation de handicap (psychomoteur, visuel)
- La gestion multiculturelle
- L'équilibre vie professionnelle / vie privée
- La collaboration avec le référent handicap

## 6. Packer

> Détail complet : voir [05-packer.md](./05-packer.md)

Template VM Ubuntu 22.04 LTS avec pré-installation des paquets requis (qemu-guest-agent, nfs-common, curl, etc.).

## 7. Terraform

> Détail complet : voir [06-terraform.md](./06-terraform.md)

Déploiement de 4 VMs via `for_each` avec génération automatique de l'inventaire Ansible.

| VM | CPU | RAM | Disque | Rôle |
|----|-----|-----|--------|------|
| k3s-server | 2 | 4 Go | 20 Go | Control-plane |
| k3s-worker-1 | 2 | 4 Go | 30 Go | Worker |
| k3s-worker-2 | 2 | 4 Go | 30 Go | Worker |
| nfs-server | 1 | 1 Go | 50 Go | Stockage NFS |

## 8. Ansible — K3s

> Détail complet : voir [07-ansible-k3s.md](./07-ansible-k3s.md)

Déploiement automatisé du cluster K3s (1 control-plane + 2 workers) via 3 rôles Ansible.

## 9. Ansible — Odoo

> Détail complet : voir [08-ansible-odoo.md](./08-ansible-odoo.md)

Déploiement via Helm de : NFS Provisioner, cert-manager, Odoo + PostgreSQL, Ingress HTTPS.

## 10. Architecture globale

> Détail complet : voir [09-architecture.md](./09-architecture.md)

Schéma complet de l'architecture réseau, des flux, et des composants Kubernetes déployés.

## 11. Captures d'écran

> **TODO** : Compléter avec les captures d'écran lors du déploiement réel

### 11.1 Proxmox — VMs déployées
<!-- ![VMs Proxmox](screenshots/proxmox-vms.png) -->
*Capture à ajouter : vue des 4 VMs dans l'interface Proxmox*

### 11.2 kubectl get nodes
<!-- ![Nodes K3s](screenshots/kubectl-nodes.png) -->
*Capture à ajouter : sortie de `kubectl get nodes -o wide` montrant les 3 noeuds Ready*

### 11.3 kubectl get pods -A
<!-- ![Pods](screenshots/kubectl-pods.png) -->
*Capture à ajouter : tous les pods du cluster (kube-system, storage, cert-manager, odoo)*

### 11.4 Interface Odoo accessible en HTTPS
<!-- ![Odoo](screenshots/odoo-interface.png) -->
*Capture à ajouter : navigateur affichant https://odoo.local avec le certificat TLS*

### 11.5 Terraform apply
<!-- ![Terraform](screenshots/terraform-apply.png) -->
*Capture à ajouter : sortie de `terraform apply` avec les 4 VMs créées*

### 11.6 Ansible playbook
<!-- ![Ansible](screenshots/ansible-playbook.png) -->
*Capture à ajouter : sortie du playbook `site.yml` montrant le déploiement réussi*

### 11.7 GitHub Actions CI
<!-- ![CI](screenshots/github-ci.png) -->
*Capture à ajouter : pipeline CI verte sur GitHub Actions*

## 12. Difficultés rencontrées et solutions

> **TODO** : Compléter au fur et à mesure du projet

| Difficulté | Solution apportée |
|------------|-------------------|
| *Exemple : Timeout lors de l'installation K3s* | *Augmentation du timeout Ansible à 120s + vérification connectivité réseau* |
| *Exemple : PVC en pending* | *Vérification du montage NFS et correction des droits sur le répertoire export* |
| ... | ... |

## 13. Conclusion

Ce projet a permis de mettre en place une infrastructure complète et entièrement automatisée pour héberger l'ERP Odoo sur un cluster Kubernetes K3s. La solution proposée répond aux exigences de la COGIP :

- **Évolutivité** : Ajout de workers via simple modification Terraform
- **Résilience** : Kubernetes redémarre automatiquement les pods en cas de panne
- **Reproductibilité** : PRA estimé à ~30 minutes via IaC (Packer + Terraform + Ansible)
- **Sécurité** : Secrets chiffrés (Ansible Vault), HTTPS (cert-manager), accès SSH par clé

## 14. Annexes

Les codes sources complets sont disponibles dans le dépôt Git :

- **Dépôt GitHub** : https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo
- `packer/` : Template Packer (ubuntu-k3s.pkr.hcl)
- `terraform/` : Recettes Terraform (main.tf, inventory.tf, etc.)
- `ansible/` : Playbooks et rôles Ansible
  - `playbooks/site.yml` : Orchestrateur principal
  - `roles/k3s-server/` : Rôle control-plane
  - `roles/k3s-agent/` : Rôle workers
  - `roles/deploy-odoo/` : Déploiement Odoo via Helm
