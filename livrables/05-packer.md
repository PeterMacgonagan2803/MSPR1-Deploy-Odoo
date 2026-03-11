# Mission 4 : Packer — Préparation des images VM

## 1. Objectif

Créer un **template de VM Ubuntu 22.04 LTS** standardisé sur Proxmox, pré-configuré avec tous les paquets nécessaires au fonctionnement de K3s et du stockage NFS. Ce template sert de base à toutes les VMs du cluster.

## 2. Pourquoi utiliser Packer ?

Sans Packer, chaque VM devrait être installée manuellement et configurée individuellement. Avec Packer :

- **Reproductibilité** : Le même template est utilisé pour toutes les VMs, garantissant une base identique.
- **PRA** : En cas de sinistre, le template peut être recréé en quelques minutes depuis le code source.
- **Gain de temps** : Les paquets sont pré-installés, réduisant le temps de provisionnement Ansible.
- **Versionnement** : Le fichier `.pkr.hcl` est versionné dans Git, traçant chaque modification.

## 3. Structure des fichiers

```
packer/
├── ubuntu-k3s.pkr.hcl      # Configuration principale (source + build)
├── variables.pkr.hcl        # Variables paramétrables
└── http/
    ├── user-data            # Cloud-init autoinstall (Ubuntu)
    └── meta-data            # Métadonnées cloud-init (vide)
```

## 4. Fonctionnement détaillé

### Phase 1 : Création de la VM temporaire

Packer crée une VM temporaire sur Proxmox à partir de l'ISO Ubuntu 22.04 avec les caractéristiques suivantes :

| Paramètre | Valeur |
|-----------|--------|
| OS | Ubuntu 22.04 LTS (`l26`) |
| CPU | 2 coeurs, type `host` |
| RAM | 4096 Mo |
| Disque | 30 Go, SCSI, format raw |
| Réseau | virtio, bridge `vmbr0` |
| Cloud-init | Activé |

### Phase 2 : Autoinstall via cloud-init

Le fichier `http/user-data` est servi via le serveur HTTP intégré de Packer. Il configure :

- **Locale** : `fr_FR.UTF-8`
- **Clavier** : Français (`fr`)
- **Utilisateur** : `ubuntu` avec droits sudo sans mot de passe
- **SSH** : Serveur SSH activé, connexion par mot de passe temporairement autorisée
- **Stockage** : LVM automatique
- **Paquets** : `qemu-guest-agent`, `curl`, `wget`, `sudo`

### Phase 3 : Provisionnement shell

Après l'installation de base, Packer exécute un provisioner `shell` qui installe les paquets requis :

```bash
sudo apt-get install -y \
  qemu-guest-agent \      # Communication Proxmox ↔ VM
  curl wget \             # Téléchargements (script K3s, Helm)
  gnupg2 \                # Gestion des clés GPG
  software-properties-common \
  apt-transport-https \
  ca-certificates \       # Certificats TLS
  nfs-common \            # Client NFS (montage volumes persistants)
  open-iscsi              # Support iSCSI (requis par certains CSI)
```

Puis nettoyage pour réduire la taille du template :

```bash
sudo apt-get autoremove -y
sudo apt-get clean
sudo cloud-init clean           # Réinitialise cloud-init pour le prochain boot
sudo truncate -s 0 /etc/machine-id  # Force la régénération d'un ID unique par VM
```

### Phase 4 : Conversion en template

Packer convertit automatiquement la VM en **template Proxmox**, prêt à être cloné par Terraform.

## 5. Variables paramétrables

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `proxmox_url` | URL API Proxmox | (requis) |
| `proxmox_username` | Utilisateur API | (requis) |
| `proxmox_password` | Mot de passe API | (requis, sensible) |
| `proxmox_node` | Nom du noeud Proxmox | (requis) |
| `iso_file` | Chemin ISO sur le stockage | `local:iso/ubuntu-22.04.4-live-server-amd64.iso` |
| `vm_id` | ID du template dans Proxmox | `9000` |
| `storage_pool` | Pool de stockage | `local-lvm` |
| `network_bridge` | Bridge réseau | `vmbr0` |

## 6. Commandes d'utilisation

```bash
cd packer
packer init .                            # Télécharge le plugin proxmox
packer validate -var-file=variables.pkr.hcl .  # Validation syntaxique
packer build -var-file=variables.pkr.hcl .     # Création du template
```

## 7. Intérêt pour le PRA de la COGIP

En cas de perte de l'infrastructure, le template VM peut être recréé en **~15 minutes** depuis le code source versionné. Combiné avec Terraform et Ansible, l'ensemble de l'infrastructure est reconstituable sans intervention manuelle, satisfaisant l'exigence de PRA du client Tesker.
