# Architecture globale de la solution

## 1. Vue d'ensemble

La solution proposée à la COGIP repose sur une architecture bare-metal virtualisée via Proxmox, hébergeant un cluster Kubernetes K3s de 3 noeuds, avec un serveur NFS dédié au stockage persistant.

## 2. Schéma d'architecture réseau

```
                    ┌─────────────────────┐
                    │   Utilisateur        │
                    │   https://odoo.local │
                    └──────────┬──────────┘
                               │
                               │ HTTPS (port 443)
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      Proxmox VE (Hyperviseur)                │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Réseau virtuel (vmbr0)                    │  │
│  │              ex: 10.0.0.0/24                           │  │
│  └──┬──────────────┬──────────────┬──────────────┬───────┘  │
│     │              │              │              │           │
│     ▼              ▼              ▼              ▼           │
│  ┌──────┐     ┌──────┐     ┌──────┐     ┌──────────┐       │
│  │ CP   │     │ W1   │     │ W2   │     │ NFS      │       │
│  │.0.10 │     │.0.11 │     │.0.12 │     │.0.13     │       │
│  │2C/4G │     │2C/4G │     │2C/4G │     │1C/1G     │       │
│  │20 Go │     │30 Go │     │30 Go │     │50 Go     │       │
│  └──┬───┘     └──┬───┘     └──┬───┘     └────┬─────┘       │
│     │            │            │               │             │
│     └──────┬─────┴────────────┘               │             │
│            │  K3s Cluster                     │             │
│            │                                  │             │
│            │  ┌─────────────────────────┐     │             │
│            │  │ kube-system             │     │             │
│            │  │  ├─ CoreDNS             │     │             │
│            │  │  ├─ Traefik (Ingress)◄──┼─ HTTPS           │
│            │  │  ├─ ServiceLB           │     │             │
│            │  │  └─ Metrics Server      │     │             │
│            │  ├─────────────────────────┤     │             │
│            │  │ storage                 │     │             │
│            │  │  └─ NFS Provisioner ────┼─────┘ NFS mount   │
│            │  ├─────────────────────────┤                   │
│            │  │ cert-manager            │                   │
│            │  │  └─ ClusterIssuer       │                   │
│            │  │     (selfsigned)        │                   │
│            │  ├─────────────────────────┤                   │
│            │  │ odoo                    │                   │
│            │  │  ├─ Odoo (pod)          │                   │
│            │  │  ├─ PostgreSQL (pod)    │                   │
│            │  │  └─ PVC ──► NFS PV     │                   │
│            │  └─────────────────────────┘                   │
│            │                                                │
└────────────┴────────────────────────────────────────────────┘
```

## 3. Flux réseau détaillé

### Accès utilisateur à Odoo

```
Utilisateur ──► DNS (odoo.local → 10.0.0.10)
            ──► Traefik (port 443, TLS termination)
            ──► Service ClusterIP odoo (port 8069)
            ──► Pod Odoo
            ──► Pod PostgreSQL (connexion interne)
            ──► PVC → NFS PV → VM NFS (/srv/nfs/k8s)
```

### Communication inter-noeuds

| Source | Destination | Port | Protocole |
|--------|-------------|------|-----------|
| Workers → Control-plane | API Server | 6443 | HTTPS |
| Control-plane → Workers | Kubelet | 10250 | HTTPS |
| Tous les noeuds | CoreDNS | 53 | UDP/TCP |
| Tous les noeuds | NFS Server | 2049 | TCP |
| Extérieur → Control-plane | Traefik | 443 | HTTPS |

## 4. Composants Kubernetes déployés

| Namespace | Composant | Type | Rôle |
|-----------|-----------|------|------|
| `kube-system` | CoreDNS | Deployment | Résolution DNS intra-cluster |
| `kube-system` | Traefik | Deployment | Ingress Controller + TLS |
| `kube-system` | ServiceLB | DaemonSet | LoadBalancer L4 |
| `kube-system` | Metrics Server | Deployment | Métriques CPU/RAM |
| `storage` | NFS Provisioner | Deployment | StorageClass dynamique |
| `cert-manager` | cert-manager | Deployment | Gestion certificats TLS |
| `cert-manager` | ClusterIssuer | CR | Émetteur autosigné |
| `odoo` | Odoo | Deployment | Application ERP |
| `odoo` | PostgreSQL | StatefulSet | Base de données |
| `odoo` | Ingress | Ingress | Route HTTPS → Odoo |

## 5. Stockage

```
Pod Odoo ──► PVC (5Gi) ──► PV ──► NFS Server (/srv/nfs/k8s/odoo-data-...)
Pod PG   ──► PVC (5Gi) ──► PV ──► NFS Server (/srv/nfs/k8s/pg-data-...)
```

Le `StorageClass` `nfs-client` (déployé via nfs-subdir-external-provisioner) crée automatiquement un sous-répertoire sur le serveur NFS pour chaque PVC demandé.

**Politique de rétention** : `Retain` — les données sont conservées même si le PVC est supprimé, garantissant la protection des données de la COGIP.

## 6. Haute disponibilité et résilience

| Composant | Résilience |
|-----------|------------|
| **Pods Odoo** | Kubernetes redémarre automatiquement les pods en cas de crash |
| **Workers** | Si un worker tombe, les pods sont replanifiés sur l'autre worker |
| **Stockage** | NFS externalisé, indépendant des workers |
| **Control-plane** | Point unique (1 seul), acceptable pour un PoC |
| **PRA** | Infrastructure entièrement reproductible via IaC en ~30 min |

> En production, il faudrait 3 control-planes et une solution de stockage répliquée (Longhorn, etc.).

## 7. Chaîne d'automatisation complète

```
 Étape 1         Étape 2              Étape 3              Étape 4
┌────────┐    ┌───────────┐    ┌──────────────┐    ┌──────────────────┐
│ Packer │───►│ Terraform │───►│ Ansible K3s  │───►│ Ansible Odoo     │
│ ~15min │    │ ~5min     │    │ ~5min        │    │ ~10min           │
│        │    │           │    │              │    │                  │
│Template│    │4 VMs      │    │Cluster 3     │    │NFS Prov          │
│VM      │    │+Inventaire│    │noeuds        │    │cert-manager      │
│        │    │Ansible    │    │              │    │Odoo + PG + Ingress│
└────────┘    └───────────┘    └──────────────┘    └──────────────────┘

Temps total estimé de reconstruction : ~30 minutes
```
