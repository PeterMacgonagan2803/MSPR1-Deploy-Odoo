# Mission 1 : Choix des technologies et justification

## 1. Contexte

La société COGIP a besoin d'une infrastructure évolutive, performante et résiliente pour héberger son ERP Odoo à destination de son client Tesker. L'infrastructure doit être entièrement reproductible via de l'Infrastructure as Code (IaC) afin de garantir un Plan de Reprise d'Activité (PRA) fiable.

## 2. Distribution Kubernetes : K3s

### Choix retenu : **K3s** (par Suse/Rancher)

### Justification

| Critère | K3s | RKE2 | K0s | MicroK8s |
|---------|-----|------|-----|----------|
| **Légèreté** | Single binary ~50Mo | Plus lourd | Léger | Snap-based |
| **LoadBalancer intégré** | Oui (ServiceLB) | Non (Calico) | Non (MetalLB requis) | Partiel |
| **Ingress intégré** | Oui (Traefik) | Non | Non | Partiel |
| **Facilité d'installation** | 1 commande curl | Moyenne | Moyenne | snap install |
| **Consommation RAM** | ~512 Mo | ~1 Go | ~512 Mo | ~800 Mo |
| **Production-ready** | Oui (certifié CNCF) | Oui | Oui | Oui |
| **Documentation** | Excellente | Bonne | Bonne | Bonne |

**Pourquoi K3s et pas les autres :**

- **LoadBalancer + Ingress intégrés** : K3s embarque nativement ServiceLB et Traefik, ce qui réduit significativement le nombre de composants à déployer et maintenir, contrairement à K0s ou RKE2 qui nécessitent MetalLB et ingress-nginx séparément.
- **Légèreté** : Un seul binaire de ~50 Mo, idéal pour un PoC avec des VMs aux ressources limitées (2 CPU / 4 Go RAM).
- **Certification CNCF** : K3s est une distribution Kubernetes certifiée conforme, garantissant la compatibilité avec l'écosystème Kubernetes standard.
- **Rapidité de déploiement** : Installation en une seule commande, réduisant le risque d'erreurs lors du provisionnement Ansible.

### Pourquoi pas une solution cloud managée (GKE, AKS, EKS) ?

- Coût mensuel non négligeable (~40-50€/mois minimum).
- Dépendance à un fournisseur cloud (vendor lock-in).
- Le bare-metal via Proxmox permet un contrôle total de l'infrastructure et une meilleure compréhension des composants sous-jacents, plus pertinent dans un contexte de PoC et d'apprentissage.

## 3. Hyperviseur : Proxmox VE

### Justification

- **Open-source** et gratuit (licence communautaire).
- **API REST complète** permettant l'automatisation via Terraform (provider `telmate/proxmox`).
- **Support de cloud-init** pour l'initialisation automatique des VMs.
- **KVM/QEMU** comme hyperviseur sous-jacent, offrant des performances proches du bare-metal.
- Largement utilisé dans les environnements de laboratoire et de formation.

## 4. Outils d'Infrastructure as Code

### Packer — Création de templates VM

| Aspect | Détail |
|--------|--------|
| **Rôle** | Créer un template de VM Ubuntu 22.04 LTS pré-configuré |
| **Pourquoi** | Garantir une base identique et reproductible pour toutes les VMs |
| **Ce qu'il installe** | qemu-guest-agent, curl, nfs-common, open-iscsi, ca-certificates |
| **Avantage PRA** | Recréation rapide des VMs à partir d'un template standardisé |

### Terraform — Provisionnement de l'infrastructure

| Aspect | Détail |
|--------|--------|
| **Rôle** | Déployer les 4 VMs sur Proxmox (clone du template Packer) |
| **Provider** | `telmate/proxmox` |
| **Pourquoi Terraform** | Déclaratif, idempotent, gestion d'état (tfstate), plan avant apply |
| **Avantage PRA** | `terraform apply` recrée l'infrastructure identique en quelques minutes |
| **Bonus** | Génération automatique de l'inventaire Ansible |

### Ansible — Configuration et déploiement applicatif

| Aspect | Détail |
|--------|--------|
| **Rôle** | Configurer les VMs, déployer K3s, installer Odoo via Helm |
| **Pourquoi Ansible** | Agentless (SSH), déclaratif, idempotent, large écosystème Galaxy |
| **Collections utilisées** | `kubernetes.core` (Helm, K8s), `ansible.posix`, `community.general` |
| **Avantage PRA** | `ansible-playbook site.yml` recrée le cluster et l'applicatif complet |

## 5. Stockage persistant : NFS + nfs-subdir-external-provisioner

- Solution la plus légère pour du stockage distant sous Kubernetes en bare-metal.
- Une VM NFS dédiée (50 Go) fournit les volumes persistants via un `StorageClass` automatique.
- Alternatives plus lourdes (Longhorn, OpenEBS) écartées car trop gourmandes en ressources pour un PoC.

## 6. Certificats TLS : cert-manager (autosignés)

- cert-manager gère automatiquement la création et le renouvellement des certificats.
- Un `ClusterIssuer` autosigné est utilisé pour le PoC (suffisant selon le cahier des charges).
- En production, passage simple vers Let's Encrypt via modification du ClusterIssuer.

## 7. Synthèse de la chaîne d'automatisation

```
ISO Ubuntu 22.04
     │
     ▼
  [Packer]  ──►  Template VM Proxmox
                      │
                      ▼
               [Terraform]  ──►  4 VMs (CP + 2 Workers + NFS)
                                    │         + inventaire Ansible auto-généré
                                    ▼
                              [Ansible]  ──►  K3s Cluster
                                               │
                                               ▼
                                         [Ansible + Helm]  ──►  NFS Provisioner
                                                                 cert-manager
                                                                 Odoo + PostgreSQL
                                                                 Ingress HTTPS
```

**Temps de reconstruction complète (PRA) estimé : ~30 minutes** depuis zéro, avec une seule commande par étape.
