variable "proxmox_url" {
  type        = string
  description = "URL de l'API Proxmox (ex: https://proxmox.local:8006/api2/json)"
}

variable "proxmox_username" {
  type        = string
  description = "Utilisateur API Proxmox (ex: root@pam ou user@pve!token)"
}

variable "proxmox_password" {
  type        = string
  sensitive   = true
  description = "Mot de passe ou token API Proxmox"
}

variable "proxmox_node" {
  type        = string
  description = "Nom du noeud Proxmox cible"
}

variable "iso_file" {
  type        = string
  default     = "local:iso/ubuntu-22.04.4-live-server-amd64.iso"
  description = "Chemin de l'ISO Ubuntu sur le stockage Proxmox"
}

variable "vm_id" {
  type        = number
  default     = 9000
  description = "ID du template VM dans Proxmox"
}

variable "storage_pool" {
  type        = string
  default     = "local-lvm"
  description = "Pool de stockage Proxmox pour les disques"
}

variable "network_bridge" {
  type        = string
  default     = "vmbr0"
  description = "Bridge réseau Proxmox"
}

variable "ssh_username" {
  type        = string
  default     = "ubuntu"
  description = "Utilisateur SSH pour le provisionnement"
}

variable "ssh_password" {
  type        = string
  default     = "ubuntu"
  sensitive   = true
  description = "Mot de passe SSH temporaire (sera remplacé par clé SSH)"
}
