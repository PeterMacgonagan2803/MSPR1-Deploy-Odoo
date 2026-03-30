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
  description = "Informations sur les VMs deployees"
  value = {
    for name, vm in proxmox_virtual_environment_vm.k3s_cluster : name => {
      id   = vm.vm_id
      name = vm.name
    }
  }
}
