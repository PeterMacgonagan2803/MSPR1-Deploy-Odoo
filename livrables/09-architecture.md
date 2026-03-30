# Architecture globale de la solution

## 1. Vue d'ensemble

La solution proposee a la COGIP repose sur une architecture bare-metal virtualisee via Proxmox VE (serveur dedie OVH), hebergeant un cluster Kubernetes K3s de 3 noeuds, avec un serveur NFS dedie au stockage persistant. Le reseau interne utilise un bridge NAT (`vmbr1`) avec port-forwarding vers l'exterieur.

## 2. Schema d'architecture reseau

```
                    +---------------------+
                    |   Utilisateur        |
                    |   http://odoo.local  |
                    +----------+----------+
                               |
                               | HTTP/HTTPS (ports 80/443)
                               v
+--------------------------------------------------------------+
|              Serveur Dedie OVH (Proxmox VE)                  |
|              IP publique : x.x.x.x                           |
|                                                              |
|  iptables NAT (PREROUTING)                                   |
|  :80  --> 10.10.10.10:80  (Traefik HTTP)                     |
|  :443 --> 10.10.10.10:443 (Traefik HTTPS)                    |
|                                                              |
|  +--------------------------------------------------------+  |
|  |           Reseau prive vmbr1 (10.10.10.0/24)           |  |
|  +--+-------------+-------------+-------------+-----------+  |
|     |             |             |             |               |
|     v             v             v             v               |
|  +------+    +------+    +------+    +----------+             |
|  | CP   |    | W1   |    | W2   |    | NFS      |             |
|  |.10.10|    |.10.11|    |.10.12|    |.10.13    |             |
|  |2C/4G |    |2C/4G |    |2C/4G |    |1C/1G    |             |
|  |20 Go |    |20 Go |    |20 Go |    |20 Go    |             |
|  +--+---+    +--+---+    +--+---+    +----+-----+             |
|     |          |          |               |                   |
|     +-----+----+----------+               |                   |
|           | K3s Cluster                   |                   |
|           |                               |                   |
|           |  +-------------------------+  |                   |
|           |  | kube-system             |  |                   |
|           |  |  +- CoreDNS             |  |                   |
|           |  |  +- Traefik (Ingress) <-+- HTTP/HTTPS          |
|           |  |  +- ServiceLB           |  |                   |
|           |  |  +- Metrics Server      |  |                   |
|           |  +-------------------------+  |                   |
|           |  | storage                 |  |                   |
|           |  |  +- NFS Provisioner ----+--->  NFS mount       |
|           |  +-------------------------+                      |
|           |  | cert-manager            |                      |
|           |  |  +- ClusterIssuer       |                      |
|           |  |    (selfsigned)         |                      |
|           |  +-------------------------+                      |
|           |  | odoo                    |                      |
|           |  |  +- PostgreSQL (pod)    |                      |
|           |  |  +- Odoo (pod)          |                      |
|           |  |  +- PVC --> NFS PV      |                      |
|           |  +-------------------------+                      |
|           |                                                   |
+--------------------------------------------------------------+
```

## 3. Flux reseau detaille

### Acces utilisateur a Odoo

```
Utilisateur --> DNS local (odoo.local -> IP publique OVH)
            --> iptables NAT sur Proxmox (port 80/443)
            --> Traefik sur K3s (Ingress Controller)
            --> Service ClusterIP odoo (port 8069)
            --> Pod Odoo
            --> Pod PostgreSQL (connexion interne port 5432)
            --> PVC -> NFS PV -> VM NFS (/srv/nfs/k8s)
```

### Communication inter-noeuds

| Source | Destination | Port | Protocole |
|--------|-------------|------|-----------|
| Exterieur -> Proxmox | iptables NAT | 80, 443 | TCP |
| Proxmox NAT -> Control-plane | Traefik | 80, 443 | TCP |
| Workers -> Control-plane | API Server | 6443 | HTTPS |
| Control-plane -> Workers | Kubelet | 10250 | HTTPS |
| Tous les noeuds | CoreDNS | 53 | UDP/TCP |
| Tous les noeuds | NFS Server | 2049 | TCP |

## 4. Composants Kubernetes deployes

| Namespace | Composant | Type | Role |
|-----------|-----------|------|------|
| `kube-system` | CoreDNS | Deployment | Resolution DNS intra-cluster |
| `kube-system` | Traefik | Deployment | Ingress Controller + TLS |
| `kube-system` | ServiceLB | DaemonSet | LoadBalancer L4 |
| `kube-system` | Metrics Server | Deployment | Metriques CPU/RAM |
| `storage` | NFS Provisioner | Deployment | StorageClass dynamique |
| `cert-manager` | cert-manager | Deployment | Gestion certificats TLS |
| `cert-manager` | ClusterIssuer | CR | Emetteur autosigne |
| `odoo` | PostgreSQL | Deployment | Base de donnees (postgres:17) |
| `odoo` | Odoo | Deployment | Application ERP (odoo:18) |
| `odoo` | Ingress | Ingress | Route HTTP/HTTPS -> Odoo |

## 5. Stockage

```
Pod Odoo --> PVC (5Gi) --> PV --> NFS Server (/srv/nfs/k8s/odoo-data-...)
Pod PG   --> PVC (5Gi) --> PV --> NFS Server (/srv/nfs/k8s/pg-data-...)
```

Le `StorageClass` `nfs-client` (deploye via nfs-subdir-external-provisioner) cree automatiquement un sous-repertoire sur le serveur NFS pour chaque PVC demande.

**Politique de retention** : `Retain` -- les donnees sont conservees meme si le PVC est supprime, garantissant la protection des donnees de la COGIP.

## 6. Haute disponibilite et resilience

| Composant | Resilience |
|-----------|------------|
| **Pods Odoo** | Kubernetes redemarre automatiquement les pods en cas de crash |
| **Workers** | Si un worker tombe, les pods sont replanifies sur l'autre worker |
| **Stockage** | NFS externalise, independant des workers |
| **Control-plane** | Point unique (1 seul), acceptable pour un PoC |
| **PRA** | Infrastructure entierement reproductible via IaC en ~50 min |

> En production, il faudrait 3 control-planes et une solution de stockage repliquee (Longhorn, etc.).

## 7. Chaine d'automatisation complete

```
 Etape 1            Etape 2              Etape 3              Etape 4
+----------+    +-------------+    +--------------+    +--------------------+
| Template |    | Terraform   |    | Ansible K3s  |    | Ansible Odoo       |
| ~3min    |--->| ~5min       |--->| ~10min       |--->| ~30min             |
|          |    |             |    |              |    |                    |
|Cloud-init|    |4 VMs        |    |Cluster 3     |    |NFS Prov            |
|Template  |    |+Inventaire  |    |noeuds        |    |cert-manager        |
|VM (9000) |    |Ansible      |    |              |    |PostgreSQL + Odoo   |
+----------+    +-------------+    +--------------+    |Ingress HTTP/HTTPS  |
                                                       +--------------------+

Temps total de reconstruction : ~50 minutes
```
