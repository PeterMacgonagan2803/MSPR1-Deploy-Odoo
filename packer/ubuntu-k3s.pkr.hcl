packer {
  required_plugins {
    proxmox = {
      version = ">= 1.1.6"
      source  = "github.com/hashicorp/proxmox"
    }
  }
}

source "proxmox-iso" "ubuntu-k3s" {
  proxmox_url              = var.proxmox_url
  username                 = var.proxmox_username
  password                 = var.proxmox_password
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  iso_file    = var.iso_file
  unmount_iso = true

  vm_id                = var.vm_id
  vm_name              = "ubuntu-k3s-template"
  template_description = "Ubuntu 22.04 LTS - Template K3s pour MSPR COGIP"

  os       = "l26"
  cpu_type = "host"
  cores    = 2
  memory   = 4096

  scsi_controller = "virtio-scsi-single"

  disks {
    type              = "scsi"
    disk_size         = "30G"
    storage_pool      = var.storage_pool
    format            = "raw"
  }

  network_adapters {
    model    = "virtio"
    bridge   = var.network_bridge
    firewall = false
  }

  cloud_init              = true
  cloud_init_storage_pool = var.storage_pool

  http_directory = "http"

  boot_command = [
    "<esc><wait>",
    "e<wait>",
    "<down><down><down><end>",
    " autoinstall ds=nocloud-net\\;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/",
    "<F10>"
  ]

  boot_wait = "10s"

  ssh_username = var.ssh_username
  ssh_password = var.ssh_password
  ssh_timeout  = "30m"

  provisioner "shell" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get upgrade -y",
      "sudo apt-get install -y qemu-guest-agent curl wget gnupg2 software-properties-common apt-transport-https ca-certificates nfs-common open-iscsi",
      "sudo systemctl enable qemu-guest-agent",
      "sudo apt-get autoremove -y",
      "sudo apt-get clean",
      "sudo cloud-init clean",
      "sudo truncate -s 0 /etc/machine-id"
    ]
  }
}

build {
  sources = ["source.proxmox-iso.ubuntu-k3s"]
}
