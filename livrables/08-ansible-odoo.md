# Mission 7 : Ansible -- Deploiement d'Odoo et mise en place de l'Ingress

## 1. Objectif

Deployer l'ERP Odoo sur le cluster K3s avec stockage persistant NFS, certificats TLS autosignes, et acces HTTP/HTTPS via l'Ingress Traefik integre.

## 2. Chaine de deploiement

```
NFS Provisioner  -->  cert-manager  -->  PostgreSQL  -->  Odoo  -->  Ingress HTTP/HTTPS
(StorageClass)       (Certificats)      (Manifests K8s) (Manifests K8s)  (Traefik)
```

## 3. Composant 1 : NFS Subdir External Provisioner

### Role
Fournir un `StorageClass` automatique (`nfs-client`) permettant a Kubernetes de creer des Persistent Volumes (PV) dynamiquement sur le serveur NFS.

### Configuration

| Parametre | Valeur |
|-----------|--------|
| Serveur NFS | IP de la VM `nfs-server` |
| Chemin export | `/srv/nfs/k8s` |
| StorageClass | `nfs-client` (defaut du cluster) |
| Politique de recuperation | `Retain` (conservation des donnees apres suppression du PVC) |

### Deploiement (Helm)
```yaml
kubernetes.core.helm:
  name: nfs-provisioner
  chart_ref: nfs-subdir-external-provisioner/nfs-subdir-external-provisioner
  release_namespace: storage
```

## 4. Composant 2 : cert-manager

### Role
Gerer automatiquement les certificats TLS pour l'Ingress HTTPS. Un `ClusterIssuer` autosigne est cree pour le PoC.

### Configuration (Helm)
```yaml
kubernetes.core.helm:
  name: cert-manager
  chart_ref: jetstack/cert-manager
  values:
    installCRDs: true
```

### ClusterIssuer autosigne
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
```

> En production, il suffit de remplacer `selfSigned` par un issuer `letsencrypt` pour obtenir des certificats valides.

## 5. Composant 3 : PostgreSQL (image officielle)

### Role
Fournir la base de donnees relationnelle necessaire a Odoo, deployee via des manifests Kubernetes natifs.

### Configuration deployee

| Parametre | Valeur |
|-----------|--------|
| Image | `postgres:17` (officielle Docker Hub) |
| Namespace | `odoo` |
| Base de donnees | `odoo` |
| Utilisateur | `odoo` |
| Mot de passe | Stocke dans Ansible Vault (`vault_pg_password`) |
| CPU | 250m request / 500m limit |
| RAM | 256Mi request / 512Mi limit |
| Stockage | 5 Gi (NFS via PVC) |

### Manifest deploye (`odoo-postgres.yml.j2`)
- **PersistentVolumeClaim** : 5Gi sur la StorageClass `nfs-client`
- **Deployment** : 1 replica PostgreSQL 17 avec subPath `pgdata`
- **Service** : ClusterIP sur le port 5432

## 6. Composant 4 : Odoo (image officielle)

### Role
Deployer l'ERP Odoo via des manifests Kubernetes natifs, connecte a PostgreSQL.

### Configuration deployee

| Parametre | Valeur |
|-----------|--------|
| Image | `odoo:18` (officielle Docker Hub) |
| Namespace | `odoo` |
| Replicas | 1 |
| CPU | 500m request / 1 limit |
| RAM | 512Mi request / 1Gi limit |
| Stockage | 5 Gi (NFS via PVC) |
| Connexion DB | Via variables d'environnement (HOST, PORT, USER, PASSWORD) |

### Pourquoi des manifests K8s plutot que Helm Bitnami ?

| Critere | Helm Bitnami | Manifests natifs |
|---------|-------------|-----------------|
| Controle | Abstraction (chart complexe) | Controle total |
| Images | Bitnami (tags parfois obsoletes) | Images officielles (stables) |
| Debug | Difficile (layers d'abstraction) | Direct (YAML lisible) |
| Dependances | Chart + sous-charts | Aucune dependance externe |

### Securisation des secrets

Les mots de passe PostgreSQL sont stockes dans `ansible/group_vars/all/vault.yml`, a chiffrer via **Ansible Vault** :

```yaml
vault_pg_password: "Ch4ng3M3!Pg2026"
```

La valeur est injectee dans les templates Jinja2 via `{{ vault_pg_password }}`.

## 7. Composant 5 : Ingress HTTP/HTTPS (Traefik)

### Configuration de l'Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: odoo-ingress
  namespace: odoo
  annotations:
    cert-manager.io/cluster-issuer: selfsigned-issuer
    traefik.ingress.kubernetes.io/router.entrypoints: web,websecure
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

1. L'utilisateur accede a `http://odoo.local` ou `https://odoo.local`
2. Traefik (Ingress Controller integre K3s) recoit la requete
3. cert-manager fournit le certificat TLS autosigne (pour HTTPS)
4. Traefik route la requete vers le service Odoo (port 8069)
5. Odoo repond avec l'interface web

### Acces

Ajouter dans le fichier `hosts` (Windows: `C:\Windows\System32\drivers\etc\hosts`) :
```
<IP_PUBLIQUE_PROXMOX>  odoo.local
```

Et configurer le port-forwarding NAT sur Proxmox (ports 80 et 443 vers le control-plane).

## 8. Health Check

Apres le deploiement, Ansible effectue un **health check HTTP** automatique :

1. Recuperation de l'IP du service Odoo dans le cluster
2. Requete GET sur `http://<IP>:8069/web/database/selector`
3. Verification du code retour HTTP 200
4. Jusqu'a 12 tentatives avec 15 secondes d'intervalle (3 minutes max)

Ce health check garantit que le deploiement est fonctionnel avant de terminer le playbook.

## 9. Commandes

```bash
# Deployer uniquement Odoo (cluster K3s deja en place)
ansible-playbook playbooks/deploy-odoo.yml --ask-vault-pass

# Deployer tout depuis zero
ansible-playbook playbooks/site.yml --ask-vault-pass
```

## 10. Resultat attendu

```
==========================================
  Deploiement MSPR COGIP termine !
==========================================

  Odoo est accessible via :
  http://odoo.local  (HTTP)
  https://odoo.local (HTTPS, certificat autosigne)

  Identifiants par defaut :
  Login    : admin
  Password : admin

  N'oubliez pas d'ajouter dans le fichier hosts :
  <IP_PUBLIQUE> odoo.local
==========================================
```
