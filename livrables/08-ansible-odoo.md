# Mission 7 : Ansible -- Deploiement d'Odoo et mise en place de l'Ingress

## 1. Objectif

Deployer l'ERP Odoo sur le cluster K3s avec stockage persistant NFS, en s'appuyant sur des **manifests Kubernetes** et les **images officielles** (`postgres:17`, `odoo:18`). L'acces utilisateur est **HTTP par defaut** (`http://odoo.local` via Ingress Traefik). Les certificats TLS via **cert-manager** sont **optionnels** : lorsqu'ils sont actives, l'Ingress expose egalement HTTPS avec des certificats autosignes adaptes au PoC.

## 2. Chaine de deploiement

```
NFS Provisioner  -->  [cert-manager] (optionnel)  -->  PostgreSQL  -->  Odoo  -->  Ingress
(StorageClass)       (TLS / ClusterIssuer)          (Manifests K8s) (Manifests K8s)  HTTP par defaut
                                                                                      HTTP+HTTPS si cert-manager
```

Les etapes **PostgreSQL**, **Odoo** et l'**Ingress** (au minimum en HTTP) sont toujours executees. **cert-manager** n'est installe et configure que si `enable_cert_manager` est vrai dans les variables de groupe.

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

## 4. Composant 2 : cert-manager (optionnel)

### Role
Lorsqu'il est active, cert-manager gere automatiquement la creation et le renouvellement des certificats TLS pour l'Ingress HTTPS. Un `ClusterIssuer` autosigne est applique pour le PoC (suffisant en laboratoire ; en production on pourrait basculer vers Let's Encrypt).

### Activation et defaut

- Le deploiement est **conditionne** par l'expression Ansible `enable_cert_manager | default(false)`.
- **Par defaut, cert-manager est desactive** (`false`), ce qui evite de dependre des images hebergees sur **quay.io** au moment du `helm install` : le registre a connu des coupures pendant le projet, ce qui bloquait entierement le playbook si cert-manager etait obligatoire.
- Pour **reactiver** cert-manager : definir `enable_cert_manager: true` dans les fichiers de group_vars (par exemple `ansible/group_vars/all/main.yml` ou un fichier dedie), puis relancer le playbook de deploiement Odoo.

### Taches conditionnees (resume)

- Ajout du depot Helm Jetstack, installation du release `cert-manager`, pause de stabilisation, application du template `ClusterIssuer` : tous ces blocs portent `when: enable_cert_manager | default(false)`.

### Configuration (Helm), lorsque active
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

> En production, il suffit de remplacer `selfSigned` par un issuer `letsencrypt` pour obtenir des certificats valides par les navigateurs.

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

## 7. Composant 5 : Ingress (Traefik) -- modes HTTP et HTTP+HTTPS

L'objet Ingress est genere a partir du template Jinja2 `odoo-ingress.yml.j2` : les blocs **annotations TLS**, **cert-manager** et la section **`spec.tls`** ne sont presents que si `enable_cert_manager | default(false)` est vrai.

### Mode par defaut : HTTP uniquement

Sans cert-manager, seul l'entrypoint **web** (HTTP) est annote ; pas de section `tls` ni d'annotation `cert-manager.io/cluster-issuer`.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: odoo-ingress
  namespace: odoo
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web
spec:
  ingressClassName: traefik
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

Le nom d'hote reel est interpole via `{{ odoo_domain | default('odoo.local') }}` dans le template.

### Mode avec cert-manager : HTTP + HTTPS (TLS)

Lorsque `enable_cert_manager` est vrai, le template ajoute l'issuer, l'annotation TLS Traefik et le bloc `tls` (secret cree par cert-manager, par exemple `odoo-tls`).

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: odoo-ingress
  namespace: odoo
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web
    cert-manager.io/cluster-issuer: selfsigned-issuer
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

1. **Par defaut** : l'utilisateur accede en priorite a **`http://odoo.local`** ; Traefik route vers le service Odoo (port 8069).
2. **Avec cert-manager** : le meme hote peut egalement etre joignable en **`https://odoo.local`** avec un certificat **autosigne** (avertissement navigateur normal en PoC).
3. Dans les deux cas, Traefik (Ingress Controller integre a K3s) termine la requete vers le backend Odoo.

### Acces

Ajouter dans le fichier `hosts` (Windows: `C:\Windows\System32\drivers\etc\hosts`) :
```
<IP_PUBLIQUE_PROXMOX>  odoo.local
```

Et configurer le port-forwarding NAT sur Proxmox (port **80** toujours ; port **443** utile surtout lorsque cert-manager et le TLS sont actives).

## 8. Health Check

Apres le deploiement, Ansible effectue un **health check HTTP** vers l'interface de selection de base (`/web/database/selector`) en utilisant l'IP **ClusterIP** du service Odoo (pas le nom DNS externe), afin de verifier une reponse applicative sans dependre du DNS poste client.

Parametres implementes dans le role :

| Parametre | Valeur |
|-----------|--------|
| URL | `http://<clusterIP>:8069/web/database/selector` |
| Codes HTTP acceptes | **200**, **303**, **500** |
| `retries` | **5** |
| `delay` | **10** secondes entre tentatives |
| `ignore_errors` | **true** |

**Justification des codes et du comportement :** pendant ou juste apres le deploiement, Odoo peut repondre par une redirection (**303**) ou exposer une page d'erreur serveur (**500**) tant que la base n'est pas initialisee ; le playbook ne doit pas echouer pour autant. L'initialisation complete de la base peut etre realisee **apres** le deploiement (connexion web). Le module `uri` enregistre le resultat ; un message de debug indique le code recu. Ainsi le health check **informe** sans bloquer la fin du playbook sur un etat transitoire.

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

  Odoo est accessible en priorite via :
  http://odoo.local

  (Si cert-manager est active : https://odoo.local
   avec certificat autosigne -- avertissement navigateur normal en PoC.)

  Identifiants par defaut :
  Login    : admin
  Password : admin

  N'oubliez pas d'ajouter dans le fichier hosts :
  <IP_PUBLIQUE> odoo.local
==========================================
```
