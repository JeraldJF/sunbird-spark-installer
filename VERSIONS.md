# Version Summary

## Helm Versions

| Component | API Version | Chart Version | Path |
|-----------|-------------|---------------|------|
| learnbb | v2 | 0.1.0 | `helmcharts/learnbb/Chart.yaml` |
| edbb | v2 | 0.1.0 | `helmcharts/edbb/Chart.yaml` |
| knowledgebb | v2 | 0.1.0 | `helmcharts/knowledgebb/Chart.yaml` |
| obsrvbb | v2 | 0.1.0 | `helmcharts/obsrvbb/Chart.yaml` |
| monitoring | v2 | 0.1.0 | `helmcharts/monitoring/Chart.yaml` |
| additional | v2 | 0.1.0 | `helmcharts/additional/Chart.yaml` |

**Notes:**
- All charts use Helm API v2 (latest as of 2026)
- ✅ Compatible with latest Helm 3.x versions
- API v2 is the current standard; v1 is deprecated

## Kubernetes Version

| Component | Current Version | Latest Version | Status | Path |
|-----------|-----------------|-----------------|--------|------|
| AKS (Azure) | 1.33.6 (auto-selected) | 1.35 | ⚠️ Behind | `opentofu/azure/modules/aks/main.tf` |
| GKE (GCP) | Not pinned | 1.35 | ❌ Unknown | `opentofu/gcp/modules/gke/main.tf` |

**Notes:**
- **AKS (Azure):** No `kubernetes_version` variable defined in module. Azure auto-selects latest stable version (currently 1.33.6)
  - No explicit version constraint - uses Azure's recommended version
  - **Latest available:** 1.35 (not yet deployed)
  - Version can change with Azure updates
- **GKE (GCP):** No explicit provider version constraint; uses latest available
- ⚠️ Risk: Different deployments may get different K8s versions

## OpenTofu / Terraform Version

| Tool | Current Version | Latest Version | Status | Path |
|------|-----------------|-----------------|--------|------|
| OpenTofu Binary | Not pinned (system default) | 1.14.7 | ❌ Unknown | `opentofu/*/template/install.sh` |
| Required Version (Azure) | Not defined | 1.14.7 | ❌ Not set | `opentofu/azure/modules/*/main.tf` |
| Required Version (GCP) | Not defined | 1.14.7 | ❌ Not set | `opentofu/gcp/modules/*/main.tf` |

**Notes:**
- No root module `required_version` constraint defined
- **Latest available:** 1.14.7 (not pinned in code)
- Deployments use whatever OpenTofu version is installed on the system (any >= 1.0)
- ⚠️ Risk: Non-reproducible deployments across different environments

## Provider Versions

| Provider | Version Constraint | Latest Version | Status | Path |
|----------|-------------------|-----------------|--------|------|
| azurerm | ~> 4.0 | 4.63 | ⚠️ Behind | `opentofu/azure/modules/aks/main.tf` |
| azurerm | ~> 4.0 | 4.63 | ⚠️ Behind | `opentofu/azure/modules/network/main.tf` |
| azurerm | ~> 4.0 | 4.63 | ⚠️ Behind | `opentofu/azure/modules/storage/main.tf` |
| azurerm | ~> 4.0.1 | 4.63 | ⚠️ Behind | `addons/dial/opentofu/azure/storage/main.tf` |
| google | ~> 5.0 | 5.x | ✅ Compatible | `opentofu/gcp/modules/random_passwords/main.tf` |
| local | ~> 2.5 | 2.5.x | ✅ Compatible | `opentofu/azure/modules/output-file/main.tf` |
| local | ~> 2.5 | 2.5.x | ✅ Compatible | `opentofu/azure/modules/upload-files/main.tf` |
| local | ~> 2.5 | 2.5.x | ✅ Compatible | `opentofu/azure/modules/random_passwords/main.tf` |
| random | ~> 3.6 | 3.6.x | ✅ Compatible | `opentofu/azure/modules/random_passwords/main.tf` |
| null | ~> 3.2 | 3.2.x | ✅ Compatible | `opentofu/azure/modules/output-file/main.tf` |
| null | ~> 3.2 | 3.2.x | ✅ Compatible | `opentofu/azure/modules/upload-files/main.tf` |
| null | ~> 3.2 | 3.2.x | ✅ Compatible | `opentofu/azure/modules/random_passwords/main.tf` |
| tls | Not defined | 4.x | ❌ Not set | `opentofu/azure/modules/keys/main.tf` |

