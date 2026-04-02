locals {
  vms = {
    "k3s-server" = {
      vmid   = 200
      cores  = 2
      memory = 4096
      disk   = 30
      ip     = var.ip_control_plane
      desc   = "K3s Control Plane - MSPR COGIP"
    }
    "k3s-worker-1" = {
      vmid   = 201
      cores  = 2
      memory = 4096
      disk   = 30
      ip     = var.ip_worker_1
      desc   = "K3s Worker 1 - MSPR COGIP"
    }
    "k3s-worker-2" = {
      vmid   = 202
      cores  = 2
      memory = 4096
      disk   = 30
      ip     = var.ip_worker_2
      desc   = "K3s Worker 2 - MSPR COGIP"
    }
    "nfs-server" = {
      vmid   = 203
      cores  = 2
      memory = 2048
      disk   = 50
      ip     = var.ip_nfs
      desc   = "Serveur NFS - Stockage persistant K8s"
    }
  }
}

resource "proxmox_virtual_environment_vm" "k3s_cluster" {
  for_each = local.vms

  name        = each.key
  vm_id       = each.value.vmid
  node_name   = var.proxmox_node
  description = each.value.desc
  on_boot     = true
  started     = true

  clone {
    vm_id = 9000
    full  = true
  }

  cpu {
    cores   = each.value.cores
    sockets = 1
    type    = "host"
  }

  memory {
    dedicated = each.value.memory
  }

  agent {
    enabled = true
  }

  operating_system {
    type = "l26"
  }

  serial_device {}

  disk {
    interface    = "scsi0"
    size         = each.value.disk
    datastore_id = var.storage_pool
    file_format  = "qcow2"
  }

  network_device {
    bridge = var.network_bridge
    model  = "virtio"
  }

  initialization {
    datastore_id = var.storage_pool

    ip_config {
      ipv4 {
        address = each.value.ip
        gateway = var.gateway
      }
    }
    dns {
      servers = [var.nameserver]
    }
    user_account {
      username = var.ssh_user
      keys     = [var.ssh_public_key]
    }
  }

  lifecycle {
    ignore_changes = [
      network_device,
    ]
  }
}
