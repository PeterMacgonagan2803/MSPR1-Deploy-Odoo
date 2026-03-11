# Mission 7 : Ansible — Déploiement d'Odoo et mise en place de l'Ingress

## 1. Objectif

Déployer l'ERP Odoo sur le cluster K3s via Helm, avec stockage persistant NFS, certificats TLS autosignés, et accès HTTPS via l'Ingress Traefik intégré.

## 2. Chaîne de déploiement

```
NFS Provisioner  ──►  cert-manager  ──►  Odoo + PostgreSQL  ──►  Ingress HTTPS
(StorageClass)       (Certificats)       (Helm Bitnami)         (Traefik)
```

Chaque composant est déployé via le module Ansible `kubernetes.core.helm`.

## 3. Composant 1 : NFS Subdir External Provisioner

### Rôle
Fournir un `StorageClass` automatique (`nfs-client`) permettant à Kubernetes de créer des Persistent Volumes (PV) dynamiquement sur le serveur NFS.

### Configuration

| Paramètre | Valeur |
|-----------|--------|
| Serveur NFS | IP de la VM `nfs-server` |
| Chemin export | `/srv/nfs/k8s` |
| StorageClass | `nfs-client` (défaut du cluster) |
| Politique de récupération | `Retain` (conservation des données après suppression du PVC) |

### Déploiement
```yaml
kubernetes.core.helm:
  name: nfs-provisioner
  chart_ref: nfs-subdir-external-provisioner/nfs-subdir-external-provisioner
  release_namespace: storage
```

## 4. Composant 2 : cert-manager

### Rôle
Gérer automatiquement les certificats TLS pour l'Ingress HTTPS. Un `ClusterIssuer` autosigné est créé pour le PoC.

### Configuration
```yaml
kubernetes.core.helm:
  name: cert-manager
  chart_ref: jetstack/cert-manager
  values:
    installCRDs: true   # Installe les Custom Resource Definitions
```

### ClusterIssuer autosigné
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
```

> En production, il suffit de remplacer `selfSigned` par un issuer `letsencrypt` pour obtenir des certificats valides.

## 5. Composant 3 : Odoo (chart Helm Bitnami)

### Rôle
Déployer l'ERP Odoo avec sa base de données PostgreSQL via la chart Helm Bitnami.

### Configuration déployée

| Paramètre | Valeur |
|-----------|--------|
| Chart | `bitnami/odoo` |
| Namespace | `odoo` |
| Email admin | `admin@cogip.local` |
| Mot de passe | Stocké dans Ansible Vault |
| Réplicas | 1 |
| CPU Odoo | 500m request / 1 limit |
| RAM Odoo | 512Mi request / 1Gi limit |
| Stockage Odoo | 5 Gi (NFS) |
| Base de données | PostgreSQL intégrée |
| Stockage PostgreSQL | 5 Gi (NFS) |
| Service | ClusterIP (exposé via Ingress) |

### Sécurisation des secrets

Les mots de passe Odoo et PostgreSQL sont stockés dans `ansible/group_vars/all/vault.yml`, chiffré via **Ansible Vault** :

```yaml
vault_odoo_password: "Ch4ng3M3!Odoo2026"
vault_pg_password: "Ch4ng3M3!Pg2026"
```

Ces valeurs sont injectées dans le template Helm via les variables Jinja2 `{{ vault_odoo_password }}` et `{{ vault_pg_password }}`.

## 6. Composant 4 : Ingress HTTPS (Traefik)

### Configuration de l'Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: odoo-ingress
  namespace: odoo
  annotations:
    cert-manager.io/cluster-issuer: selfsigned-issuer
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - odoo.local
      secretName: odoo-tls
  rules:
    - host: odoo.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: odoo
                port:
                  number: 8069
```

### Fonctionnement

1. L'utilisateur accède à `https://odoo.local`
2. Traefik (Ingress Controller intégré K3s) reçoit la requête
3. cert-manager fournit le certificat TLS autosigné
4. Traefik route la requête vers le service Odoo (port 8069)
5. Odoo répond avec l'interface web

### Accès

Ajouter dans le fichier `/etc/hosts` (ou DNS local) :
```
<IP_CONTROL_PLANE>  odoo.local
```

## 7. Health Check

Après le déploiement, Ansible effectue un **health check HTTP** automatique :

1. Récupération de l'IP du service Odoo dans le cluster
2. Requête GET sur `http://<IP>:8069/web/database/selector`
3. Vérification du code retour HTTP 200
4. Jusqu'à 12 tentatives avec 15 secondes d'intervalle (3 minutes max)

Ce health check garantit que le déploiement est fonctionnel avant de terminer le playbook.

## 8. Commandes

```bash
# Déployer uniquement Odoo (cluster K3s déjà en place)
ansible-playbook playbooks/deploy-odoo.yml --ask-vault-pass

# Déployer tout depuis zéro
ansible-playbook playbooks/site.yml --ask-vault-pass
```

## 9. Résultat attendu

```
==========================================
  Déploiement MSPR COGIP terminé !
==========================================

  Odoo est accessible via :
  https://odoo.local

  Identifiants par défaut :
  Email : admin@cogip.local
  Mot de passe : (vault)

  N'oubliez pas d'ajouter dans /etc/hosts :
  10.0.0.10 odoo.local
==========================================
```
