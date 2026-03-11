locals {
  vms = {
    "k3s-server" = {
      vmid   = 200
      cores  = 2
      memory = 4096
      disk   = "20G"
      ip     = var.ip_control_plane
      desc   = "K3s Control Plane - MSPR COGIP"
    }
    "k3s-worker-1" = {
      vmid   = 201
      cores  = 2
      memory = 4096
      disk   = "30G"
      ip     = var.ip_worker_1
      desc   = "K3s Worker 1 - MSPR COGIP"
    }
    "k3s-worker-2" = {
      vmid   = 202
      cores  = 2
      memory = 4096
      disk   = "30G"
      ip     = var.ip_worker_2
      desc   = "K3s Worker 2 - MSPR COGIP"
    }
    "nfs-server" = {
      vmid   = 203
      cores  = 1
      memory = 1024
      disk   = "50G"
      ip     = var.ip_nfs
      desc   = "Serveur NFS - Stockage persistant K8s"
    }
  }
}

resource "proxmox_vm_qemu" "k3s_cluster" {
  for_each = local.vms

  name        = each.key
  vmid        = each.value.vmid
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = true
  agent       = 1
  desc        = each.value.desc

  cores   = each.value.cores
  sockets = 1
  cpu     = "host"
  memory  = each.value.memory

  os_type    = "cloud-init"
  scsihw     = "virtio-scsi-single"
  bootdisk   = "scsi0"
  onboot     = true
  automatic_reboot = true

  disks {
    scsi {
      scsi0 {
        disk {
          size    = each.value.disk
          storage = var.storage_pool
          format  = "raw"
        }
      }
    }
  }

  network {
    model  = "virtio"
    bridge = var.network_bridge
  }

  ipconfig0  = "ip=${each.value.ip},gw=${var.gateway}"
  nameserver = var.nameserver
  ciuser     = var.ssh_user
  sshkeys    = var.ssh_public_key

  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}
