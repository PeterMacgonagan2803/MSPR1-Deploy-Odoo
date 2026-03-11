output "control_plane_ip" {
  description = "Adresse IP du control-plane K3s"
  value       = split("/", var.ip_control_plane)[0]
}

output "worker_1_ip" {
  description = "Adresse IP du worker 1"
  value       = split("/", var.ip_worker_1)[0]
}

output "worker_2_ip" {
  description = "Adresse IP du worker 2"
  value       = split("/", var.ip_worker_2)[0]
}

output "nfs_server_ip" {
  description = "Adresse IP du serveur NFS"
  value       = split("/", var.ip_nfs)[0]
}

output "vm_info" {
  description = "Informations sur les VMs déployées"
  value = {
    for name, vm in proxmox_vm_qemu.k3s_cluster : name => {
      id     = vm.vmid
      name   = vm.name
      cores  = vm.cores
      memory = vm.memory
    }
  }
}

output "ansible_inventory_hint" {
  description = "Aide pour la configuration de l'inventaire Ansible"
  value       = <<-EOT
    Mettez à jour ansible/inventory/hosts.yml avec les IPs suivantes :
    - control_plane: ${split("/", var.ip_control_plane)[0]}
    - worker_1:      ${split("/", var.ip_worker_1)[0]}
    - worker_2:      ${split("/", var.ip_worker_2)[0]}
    - nfs_server:    ${split("/", var.ip_nfs)[0]}
  EOT
}
