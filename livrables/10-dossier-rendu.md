# Mission 8 : Dossier de rendu final -- MSPR COGIP

## Sommaire

1. [Introduction et contexte](#1-introduction-et-contexte)
2. [Choix des technologies](#2-choix-des-technologies)
3. [Organisation du projet](#3-organisation-du-projet)
4. [Suivi de l'avancement](#4-suivi-de-lavancement)
5. [Mesures d'inclusivite](#5-mesures-dinclusivite)
6. [Preparation des images VM](#6-preparation-des-images)
7. [Terraform -- Deploiement de l'infrastructure](#7-terraform)
8. [Ansible -- Deploiement de Kubernetes](#8-ansible-k3s)
9. [Ansible -- Deploiement d'Odoo](#9-ansible-odoo)
10. [Architecture globale](#10-architecture-globale)
11. [Captures d'ecran et preuves](#11-captures-decran)
12. [Difficultes rencontrees et solutions](#12-difficultes-et-solutions)
13. [Conclusion](#13-conclusion)
14. [Annexes](#14-annexes)

---

## 1. Introduction et contexte

La societe COGIP, specialisee dans les ERP, a decroche un contrat avec le groupe Tesker (vehicules electriques). Notre entreprise a remporte l'appel d'offres pour la mise en place d'une infrastructure hebergeant l'ERP Odoo, repondant aux criteres suivants :
- **Evolutivite** : capacite de dimensionnement facile
- **Performance** : ressources adaptees a Odoo
- **Resilience** : resistance aux pannes
- **Reproductibilite** : Infrastructure as Code pour le PRA

La solution proposee : un cluster **Kubernetes K3s** deploye via **Terraform + Ansible** sur **Proxmox VE** (serveur dedie OVH).

## 2. Choix des technologies

> Detail complet : voir [01-choix-technologies.md](./01-choix-technologies.md)

**Resume** :
- **K3s** : Distribution K8s legere, certifiee CNCF, avec LoadBalancer et Ingress Traefik integres
- **Proxmox VE** : Hyperviseur open-source avec API REST complete
- **Cloud-init** : Templates VM reproductibles (alternative legere a Packer)
- **Terraform** : Provisionnement declaratif de l'infrastructure (provider `bpg/proxmox`)
- **Ansible** : Configuration agentless et deploiement applicatif
- **NFS** : Stockage persistant leger pour le PoC
- **cert-manager** : Certificats TLS automatiques (autosignes pour le PoC)

## 3. Organisation du projet

> Detail complet : voir [02-gantt.md](./02-gantt.md)

Le projet a ete decoupe en **15 taches** reparties sur les 19 heures de preparation. Un diagramme de Gantt (format Mermaid) detaille le planning previsionnel et les dependances entre taches.

## 4. Suivi de l'avancement

> Detail complet : voir [03-kanban.md](./03-kanban.md)

Un tableau Kanban a 4 colonnes (A faire -> En cours -> Revue Technique -> Termine) a ete utilise pour suivre les 19 tickets du projet. La revue technique a ete realisee collectivement.

## 5. Mesures d'inclusivite

> Detail complet : voir [04-inclusivite.md](./04-inclusivite.md)

Des mesures concretes ont ete definies pour :
- L'accueil de personnes en situation de handicap (psychomoteur, visuel)
- La gestion multiculturelle
- L'equilibre vie professionnelle / vie privee
- La collaboration avec le referent handicap

## 6. Preparation des images

> Detail complet : voir [05-packer.md](./05-packer.md)

Template VM Ubuntu 22.04 LTS cree via image cloud officielle + cloud-init, convertie en template Proxmox (ID 9000). Les fichiers Packer sont conserves comme approche alternative documentee.

## 7. Terraform

> Detail complet : voir [06-terraform.md](./06-terraform.md)

Deploiement de 4 VMs via `for_each` avec generation automatique de l'inventaire Ansible. Provider `bpg/proxmox`.

| VM | CPU | RAM | Disque | Role |
|----|-----|-----|--------|------|
| k3s-server | 2 | 4 Go | 20 Go | Control-plane |
| k3s-worker-1 | 2 | 4 Go | 20 Go | Worker |
| k3s-worker-2 | 2 | 4 Go | 20 Go | Worker |
| nfs-server | 1 | 1 Go | 20 Go | Stockage NFS |

## 8. Ansible -- K3s

> Detail complet : voir [07-ansible-k3s.md](./07-ansible-k3s.md)

Deploiement automatise du cluster K3s (1 control-plane + 2 workers) via 3 roles Ansible.

## 9. Ansible -- Odoo

> Detail complet : voir [08-ansible-odoo.md](./08-ansible-odoo.md)

Deploiement via manifests Kubernetes natifs de : NFS Provisioner (Helm), cert-manager (Helm), PostgreSQL 17, Odoo 18, Ingress HTTP/HTTPS (Traefik).

## 10. Architecture globale

> Detail complet : voir [09-architecture.md](./09-architecture.md)

Schema complet de l'architecture reseau (NAT, vmbr1, port-forwarding), des flux, et des composants Kubernetes deployes.

## 11. Captures d'ecran

> **TODO** : Completer avec les captures d'ecran du deploiement reel

### 11.1 Proxmox -- VMs deployees
<!-- ![VMs Proxmox](screenshots/proxmox-vms.png) -->
*Capture a ajouter : vue des 4 VMs dans l'interface Proxmox*

### 11.2 kubectl get nodes
<!-- ![Nodes K3s](screenshots/kubectl-nodes.png) -->
*Capture a ajouter : sortie de `kubectl get nodes -o wide` montrant les 3 noeuds Ready*

### 11.3 kubectl get pods -A
<!-- ![Pods](screenshots/kubectl-pods.png) -->
*Capture a ajouter : tous les pods du cluster (kube-system, storage, cert-manager, odoo)*

### 11.4 Interface Odoo accessible
<!-- ![Odoo](screenshots/odoo-interface.png) -->
*Capture a ajouter : navigateur affichant http://odoo.local avec l'interface Odoo*

### 11.5 Terraform apply
<!-- ![Terraform](screenshots/terraform-apply.png) -->
*Capture a ajouter : sortie de `terraform apply` avec les 4 VMs creees*

### 11.6 Ansible playbook
<!-- ![Ansible](screenshots/ansible-playbook.png) -->
*Capture a ajouter : sortie du playbook `site.yml` montrant le deploiement reussi*

## 12. Difficultes rencontrees et solutions

| Difficulte | Solution apportee |
|------------|-------------------|
| Provider Terraform `telmate/proxmox` : erreurs de permissions (`VM.Monitor`) meme avec des tokens privilegies | Migration vers le provider `bpg/proxmox` qui gere mieux l'authentification par mot de passe et le SSH natif |
| Packer : echec de l'autoinstall Ubuntu (l'installeur manuel se lancait au lieu du mode cloud-init) | Abandon de Packer + ISO au profit d'un script utilisant l'image cloud Ubuntu qcow2 avec cloud-init natif |
| Images Docker Bitnami Odoo : tags obsoletes non disponibles sur Docker Hub | Remplacement du chart Helm Bitnami par des manifests Kubernetes natifs avec les images officielles `odoo:18` et `postgres:17` |
| Timeout SSH lors de l'execution d'Ansible depuis Windows vers les VMs via Proxmox | Execution d'Ansible directement sur le serveur Proxmox (plus proche des VMs) avec scripts Python/Paramiko pour l'orchestration |
| Traefik retournait 404 en HTTP : l'Ingress ne routait que le trafic HTTPS (`websecure`) | Ajout d'un IngressRoute Traefik CRD pour le trafic HTTP (`web`) en complement de l'Ingress standard |
| QEMU Guest Agent : Terraform bloquait indefiniment en attendant l'agent non installe | Desactivation de l'agent dans la configuration Terraform (`agent { enabled = false }`) |
| Reseau Proxmox : VMs sur reseau prive non accessibles depuis l'exterieur | Configuration NAT avec `vmbr1` (bridge prive) et regles iptables pour le port-forwarding (80, 443) |

## 13. Conclusion

Ce projet a permis de mettre en place une infrastructure complete et entierement automatisee pour heberger l'ERP Odoo sur un cluster Kubernetes K3s. La solution proposee repond aux exigences de la COGIP :

- **Evolutivite** : Ajout de workers via simple modification Terraform
- **Resilience** : Kubernetes redemarre automatiquement les pods en cas de panne
- **Reproductibilite** : PRA estime a ~50 minutes via IaC (Template + Terraform + Ansible)
- **Securite** : Secrets proteges (Ansible Vault), HTTPS (cert-manager), acces SSH par cle

## 14. Annexes

Les codes sources complets sont disponibles dans le depot Git :

- **Depot GitHub** : https://github.com/PeterMacgonagan2803/MSPR1-Deploy-Odoo
- `setup/` : Scripts de deploiement (template VM, configuration reseau, outils)
- `terraform/` : Recettes Terraform (provider `bpg/proxmox`, VMs, inventaire)
- `ansible/` : Playbooks et roles Ansible
  - `playbooks/site.yml` : Orchestrateur principal
  - `roles/k3s-server/` : Role control-plane
  - `roles/k3s-agent/` : Role workers
  - `roles/deploy-odoo/` : Deploiement Odoo + PostgreSQL via manifests K8s
- `packer/` : Approche alternative Packer (conservee pour reference)
- `livrables/` : Documentation detaillee par mission
