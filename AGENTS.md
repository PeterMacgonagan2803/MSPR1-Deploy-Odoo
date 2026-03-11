# AGENTS.md

## Cursor Cloud specific instructions

This is an Infrastructure-as-Code (IaC) project (no application source code). The "development loop" consists of editing Terraform/Packer/Ansible files and running the CI validation checks locally.

### Tools required

| Tool | Version | Purpose |
|------|---------|---------|
| Terraform | >= 1.5 (CI uses 1.7.0) | Provisioning VMs on Proxmox |
| Packer | >= 1.9 (CI uses 1.10.0) | Building VM templates |
| Ansible + ansible-lint | >= 2.15 | Configuring K3s cluster and deploying Odoo |

### Running CI checks locally

The CI pipeline (`.github/workflows/ci.yml`) runs three jobs. To replicate them locally:

```bash
# 1. Terraform — init, fmt, validate
cd terraform && terraform init -backend=false && terraform fmt -check -recursive && terraform validate

# 2. Packer — init, fmt, validate
cd packer && packer init . && packer fmt -check . && packer validate -syntax-only .

# 3. Ansible — install galaxy collections, then lint
cd ansible && ansible-galaxy collection install -r requirements.yml && ansible-lint playbooks/ roles/
```

### Known issues (pre-existing on main)

- **Terraform init fails**: The provider constraint `telmate/proxmox >= 3.0.1` in `terraform/providers.tf` does not match any published release. This causes `terraform init` (and therefore `terraform validate`) to fail. This is also failing in CI on `main`.
- **Terraform fmt**: `inventory.tf` and `main.tf` have formatting differences (`terraform fmt -check` exits non-zero). This is also pre-existing on `main`.
- **Ansible-lint**: Reports 29 violations (ignore-errors, yaml truthy, command-instead-of-module, etc.). All are pre-existing on `main`.

### Caveats

- `ansible-lint` is installed in `~/.local/bin`; ensure this is on `PATH` (the update script handles this via the `--break-system-packages` pip install which places it there; `~/.bashrc` exports it).
- Ansible Galaxy collections must be installed before running `ansible-lint` (the `kubernetes.core` collection is required by the deploy-odoo role).
- Packer and Terraform are installed as single binaries in `/usr/local/bin/`.
