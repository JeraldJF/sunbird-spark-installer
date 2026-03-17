# Infrastructure Upgrade - Implementation Checklist

**Start Date:** ___________
**Target Completion:** ___________
**Project Owner:** ___________

---

## PHASE 1: Lock Down Reproducibility ✅
**Duration:** ~30 minutes
**Parallelizable:** YES
**Risk Level:** 🟢 LOW

### 1.1 Azure Root Module (main.tf)
- [ ] Create file: `opentofu/azure/template/main.tf`
- [ ] Add terraform block with required_version
- [ ] Add all required_providers (azurerm, local, random, null, tls)
- [ ] Verify syntax: `cd opentofu/azure/template && tofu init`
- [ ] No errors on init
- **Completed by:** ___________
- **Verified by:** ___________

### 1.2 GCP Root Module (main.tf)
- [ ] Create file: `opentofu/gcp/template/main.tf`
- [ ] Add terraform block with required_version
- [ ] Add all required_providers (google, local, random, null, tls)
- [ ] Verify syntax: `cd opentofu/gcp/template && tofu init`
- [ ] No errors on init
- **Completed by:** ___________
- **Verified by:** ___________

### 1.3 Remove -upgrade Flag (Azure)
- [ ] Edit: `opentofu/azure/template/install.sh`
- [ ] Find line with: `tofu init -upgrade`
- [ ] Change to: `tofu init`
- [ ] Test: `bash install.sh` (dry-run with valid inputs)
- **Completed by:** ___________
- **Verified by:** ___________

### 1.4 Remove -upgrade Flag (GCP)
- [ ] Edit: `opentofu/gcp/template/install.sh`
- [ ] Find line with: `tofu init -upgrade`
- [ ] Change to: `tofu init`
- [ ] Test: `bash install.sh` (dry-run with valid inputs)
- **Completed by:** ___________
- **Verified by:** ___________

### 1.5 Populate Lock Files
- [ ] Run: `cd opentofu/azure/template && tofu init`
  - [ ] File created: `.opentofu.lock.hcl`
  - [ ] Contains provider version pins
- [ ] Run: `cd opentofu/gcp/template && tofu init`
  - [ ] File created: `.opentofu.lock.hcl`
  - [ ] Contains provider version pins
- [ ] Commit to git:
  - [ ] `git add opentofu/azure/template/.opentofu.lock.hcl`
  - [ ] `git add opentofu/gcp/template/.opentofu.lock.hcl`
  - [ ] `git commit -m "Lock provider versions for reproducibility"`
- [ ] Push to main (or open PR)
- **Completed by:** ___________
- **Verified by:** ___________

### 1.6 Align DIAL Addon
- [ ] Edit: `addons/dial/opentofu/azure/storage/main.tf`
- [ ] Change: `azurerm ~> 4.0.1` → `azurerm ~> 4.0`
- [ ] Verify: `cd addons/dial/opentofu/azure/storage && tofu validate`
- [ ] No errors
- **Completed by:** ___________
- **Verified by:** ___________

### Phase 1 Sign-Off
- [ ] All 6 tasks completed
- [ ] All changes committed to git
- [ ] No `tofu plan` shows unexpected changes
- [ ] Lock files in version control
- **Signed off by:** ___________ **Date:** ___________

---

## PHASE 2: Provider Standardization ✅
**Duration:** ~45 minutes
**Parallelizable:** YES (2.1 and 2.2 independent)
**Risk Level:** 🟡 LOW-MEDIUM

### 2.1 Update GCP Module Constraints (7 modules)

#### 2.1.1 - gke/main.tf
- [ ] Edit: `opentofu/gcp/modules/gke/main.tf`
- [ ] Add terraform block with google provider ~> 5.0
- [ ] Verify: `cd opentofu/gcp/modules/gke && tofu validate`
- **Completed by:** ___________

#### 2.1.2 - network/main.tf
- [ ] Edit: `opentofu/gcp/modules/network/main.tf`
- [ ] Add terraform block with google provider ~> 5.0
- [ ] Verify: `cd opentofu/gcp/modules/network && tofu validate`
- **Completed by:** ___________

#### 2.1.3 - service-account/main.tf
- [ ] Edit: `opentofu/gcp/modules/service-account/main.tf`
- [ ] Add terraform block with google provider ~> 5.0
- [ ] Verify: `cd opentofu/gcp/modules/service-account && tofu validate`
- **Completed by:** ___________

#### 2.1.4 - storage/main.tf
- [ ] Edit: `opentofu/gcp/modules/storage/main.tf`
- [ ] Add terraform block with google provider ~> 5.0
- [ ] Verify: `cd opentofu/gcp/modules/storage && tofu validate`
- **Completed by:** ___________

#### 2.1.5 - upload-files/main.tf
- [ ] Edit: `opentofu/gcp/modules/upload-files/main.tf`
- [ ] Add terraform block with local ~> 2.5
- [ ] Verify: `cd opentofu/gcp/modules/upload-files && tofu validate`
- **Completed by:** ___________

#### 2.1.6 - output-file/main.tf
- [ ] Edit: `opentofu/gcp/modules/output-file/main.tf`
- [ ] Add terraform block with local ~> 2.5
- [ ] Verify: `cd opentofu/gcp/modules/output-file && tofu validate`
- **Completed by:** ___________

#### 2.1.7 - keys/main.tf
- [ ] Edit: `opentofu/gcp/modules/keys/main.tf`
- [ ] Add terraform block with tls ~> 4.0
- [ ] Verify: `cd opentofu/gcp/modules/keys && tofu validate`
- **Completed by:** ___________

### 2.2 Update Azure Module Constraints

#### 2.2.1 - keys/main.tf (TLS Constraint)
- [ ] Edit: `opentofu/azure/modules/keys/main.tf`
- [ ] Add terraform block with tls ~> 4.0
- [ ] Verify: `cd opentofu/azure/modules/keys && tofu validate`
- [ ] No errors
- **Completed by:** ___________

#### 2.2.2 - Audit Other Azure Modules
- [ ] Verify aks/main.tf has azurerm ~> 4.0 ✅
- [ ] Verify network/main.tf has azurerm ~> 4.0 ✅
- [ ] Verify storage/main.tf has azurerm ~> 4.0 ✅
- [ ] Verify output-file/main.tf has constraints ✅
- [ ] Verify upload-files/main.tf has constraints ✅
- [ ] Verify random_passwords/main.tf has constraints ✅
- **Completed by:** ___________

### Phase 2 Sign-Off
- [ ] All 8 modules updated with explicit providers
- [ ] All modules validate successfully
- [ ] Changes committed to git
- [ ] `tofu plan` shows no unexpected changes
- **Signed off by:** ___________ **Date:** ___________

---

## PHASE 3: Kubernetes Version Pinning ✅
**Duration:** ~1 hour
**Parallelizable:** YES (3.1 and 3.2 independent)
**Risk Level:** 🟡 MEDIUM

### 3.1 Pin AKS Kubernetes Version

#### 3.1.1 - Update AKS Module
- [ ] Edit: `opentofu/azure/modules/aks/main.tf`
- [ ] Add `kubernetes_version` variable with default "1.33.6"
- [ ] Add validation block (1.33-1.35 range)
- [ ] Update azurerm_kubernetes_cluster resource: `kubernetes_version = var.kubernetes_version`
- [ ] Verify: `cd opentofu/azure/modules/aks && tofu validate`
- **Completed by:** ___________

#### 3.1.2 - Update All Azure Environment Variables
- [ ] Edit: `opentofu/azure/dev/terraform.tfvars`
  - [ ] Add: `kubernetes_version = "1.33.6"`
- [ ] Edit: `opentofu/azure/staging/terraform.tfvars`
  - [ ] Add: `kubernetes_version = "1.33.6"`
- [ ] Edit: `opentofu/azure/production/terraform.tfvars`
  - [ ] Add: `kubernetes_version = "1.33.6"`
- [ ] Dry-run plan: `cd opentofu/azure/dev && tofu plan`
  - [ ] Should show: "No changes. Your infrastructure matches the configuration."
- **Completed by:** ___________

### 3.2 Pin GKE Kubernetes Version

#### 3.2.1 - Update GKE Module
- [ ] Edit: `opentofu/gcp/modules/gke/main.tf`
- [ ] Add `kubernetes_version` variable with default "1.33.0"
- [ ] Add `release_channel` variable with default "REGULAR"
- [ ] Update google_container_cluster resource:
  - [ ] `min_master_version = var.kubernetes_version`
  - [ ] `release_channel { channel = var.release_channel }`
- [ ] Verify: `cd opentofu/gcp/modules/gke && tofu validate`
- **Completed by:** ___________

#### 3.2.2 - Update All GCP Environment Variables
- [ ] Edit: `opentofu/gcp/dev/terraform.tfvars`
  - [ ] Add: `kubernetes_version = "1.33.0"`
  - [ ] Add: `release_channel = "REGULAR"`
- [ ] Edit: `opentofu/gcp/staging/terraform.tfvars`
  - [ ] Add: `kubernetes_version = "1.33.0"`
  - [ ] Add: `release_channel = "REGULAR"`
- [ ] Edit: `opentofu/gcp/production/terraform.tfvars`
  - [ ] Add: `kubernetes_version = "1.33.0"`
  - [ ] Add: `release_channel = "REGULAR"`
- [ ] Dry-run plan: `cd opentofu/gcp/dev && tofu plan`
  - [ ] Should show: "No changes. Your infrastructure matches the configuration."
- **Completed by:** ___________

### 3.3 Document Version Policy
- [ ] Create: `docs/KUBERNETES_VERSION_POLICY.md`
- [ ] Include version support matrix
- [ ] Document upgrade path
- [ ] List component compatibility
- [ ] Include upgrade procedure steps
- [ ] Commit to git
- **Completed by:** ___________

### Phase 3 Sign-Off
- [ ] AKS module has explicit K8s version variable
- [ ] GKE module has explicit K8s version variable
- [ ] All environment terraform.tfvars updated
- [ ] Dry-run plans show no changes
- [ ] Version policy documented
- [ ] All changes committed
- **Signed off by:** ___________ **Date:** ___________

---

## PHASE 4: Kubernetes Cluster Upgrades 🚀
**Duration:** 4-6 hours per cluster
**Parallelizable:** Staging can run while dev validates
**Risk Level:** 🟠 MEDIUM

### Pre-Upgrade Checklist (for each cluster)
- [ ] Backup cluster with Velero
- [ ] Schedule maintenance window (off-peak)
- [ ] Notify stakeholders of potential transient downtime
- [ ] Have rollback plan ready

### 4.1 Dev Cluster: 1.33.6 → 1.34.0

#### 4.1.1 - Plan Upgrade
- [ ] Edit: `opentofu/azure/dev/terraform.tfvars`
  - [ ] Change: `kubernetes_version = "1.34.0"`
- [ ] Plan: `cd opentofu/azure/dev && tofu plan -out=plan.out`
- [ ] Review plan:
  - [ ] Only AKS cluster update (no data loss)
  - [ ] No changes to other resources
- **Completed by:** ___________

#### 4.1.2 - Apply Upgrade
- [ ] Time: ___________  Duration: ___________ minutes
- [ ] Apply: `tofu apply plan.out`
- [ ] Monitor upgrade (Azure will show progress):
  - [ ] Master nodes upgrade first (no downtime)
  - [ ] Worker nodes upgrade sequentially
  - [ ] Total time: 30-60 minutes
- [ ] Post-upgrade verification:
  - [ ] `kubectl version --short`
    - Output should show v1.34.x
  - [ ] `kubectl get nodes -o wide`
    - All nodes should show 1.34.x
  - [ ] `kubectl get pods -A`
    - All pods should be Running
- **Completed by:** ___________

#### 4.1.3 - Validate Workloads (24 hours)
- [ ] Hour 0-1: Initial validation
  - [ ] All pods running
  - [ ] Services responding
  - [ ] No error logs
- [ ] Hour 1-4: Function testing
  - [ ] Login to application (Kong API)
  - [ ] Create test content
  - [ ] Verify database connectivity
  - [ ] Check Flink jobs processing
- [ ] Hour 4-24: Stability monitoring
  - [ ] Monitor Prometheus metrics
  - [ ] Check Grafana dashboards
  - [ ] No resource exhaustion
  - [ ] No restart loops
- [ ] Approval to proceed to Staging: ___________
- **Completed by:** ___________

### 4.2 Staging Cluster: 1.33.6 → 1.34.0

#### 4.2.1 - Plan Upgrade
- [ ] Edit: `opentofu/azure/staging/terraform.tfvars`
  - [ ] Change: `kubernetes_version = "1.34.0"`
- [ ] Plan: `cd opentofu/azure/staging && tofu plan -out=plan.out`
- [ ] Review plan
- **Completed by:** ___________

#### 4.2.2 - Apply Upgrade
- [ ] Time: ___________  Duration: ___________ minutes
- [ ] Apply: `tofu apply plan.out`
- [ ] Monitor progress
- [ ] Verify all nodes at 1.34.x
- [ ] Verify all pods running
- **Completed by:** ___________

#### 4.2.3 - Validate Workloads (8-12 hours)
- [ ] Shorter validation than dev (already proven)
- [ ] All pods running
- [ ] Services responding
- [ ] No errors in logs
- [ ] Approval to proceed to Production: ___________
- **Completed by:** ___________

### 4.3 Production Cluster: 1.33.6 → 1.34.0

#### 4.3.1 - Pre-Production Checklist
- [ ] Backup verified in Velero
- [ ] Maintenance window scheduled
- [ ] Stakeholders notified
- [ ] On-call engineer on standby
- [ ] Rollback procedure reviewed
- **Ready:** ___________

#### 4.3.2 - Plan Upgrade
- [ ] Edit: `opentofu/azure/production/terraform.tfvars`
  - [ ] Change: `kubernetes_version = "1.34.0"`
- [ ] Plan: `cd opentofu/azure/production && tofu plan -out=plan.out`
- [ ] Review plan carefully (should be identical to staging)
- [ ] Get approval: ___________
- **Completed by:** ___________

#### 4.3.3 - Apply Upgrade
- [ ] Time: ___________  Duration: ___________ minutes
- [ ] **Important:** Upgrade during maintenance window
- [ ] Apply: `tofu apply plan.out`
- [ ] Monitor continuously (have dashboards open)
- [ ] Node upgrades should take 30-60 minutes
- [ ] Post-upgrade verification:
  - [ ] All nodes at 1.34.x
  - [ ] All pods running
  - [ ] Services responding
  - [ ] No application errors
- **Completed by:** ___________

#### 4.3.4 - Post-Upgrade Validation (24+ hours)
- [ ] Metrics look normal (no spikes)
- [ ] No increased error rates
- [ ] User reports positive
- [ ] Stakeholder sign-off
- [ ] Ready to document completion
- **Completed by:** ___________

### Phase 4 Sign-Off
- [ ] Dev cluster: ✅ 1.34.0 stable for 24 hours
- [ ] Staging cluster: ✅ 1.34.0 stable for 8+ hours
- [ ] Production cluster: ✅ 1.34.0 stable for 24+ hours
- [ ] No rollbacks needed
- [ ] All changes committed (terraform.tfvars updated)
- **Signed off by:** ___________ **Date:** ___________

---

## PHASE 5: Long-Term Maintenance 📋
**Duration:** Ongoing
**Risk Level:** 🟡 MEDIUM

### 5.1 Provider Major Version Planning
- [ ] Schedule quarterly review of provider updates
- [ ] Review breaking changes for azurerm 5.0
- [ ] Plan migration strategy (target: Q3-Q4 2026)
- [ ] Document breaking changes
- **Scheduled for:** ___________

### 5.2 Next Kubernetes Upgrade (1.34 → 1.35)
- [ ] Planned for: ___________  (4-6 weeks after 1.34 stable)
- [ ] Repeat Phase 4 procedures
- [ ] Use same dev → staging → production flow

### 5.3 Team Training
- [ ] [ ] Document version upgrade process for team
- [ ] [ ] Conduct training session
- [ ] [ ] Create runbooks for common upgrades
- [ ] [ ] Establish version update policy

### 5.4 CI/CD Improvements
- [ ] [ ] Add version validation to CI/CD pipeline
- [ ] [ ] Automate `tofu validate` on all modules
- [ ] [ ] Track provider version updates
- [ ] [ ] Alert on new major versions

### 5.5 Docker-Based OpenTofu (Optional)
- [ ] [ ] Evaluate Docker-based deployments
- [ ] [ ] Create OpenTofu Docker image
- [ ] [ ] Migrate CI/CD to use Docker version
- [ ] **Timeline:** 2026-Q3

### Phase 5 Sign-Off
- [ ] Processes documented
- [ ] Team trained
- [ ] Future upgrades planned
- **Signed off by:** ___________ **Date:** ___________

---

## Overall Project Sign-Off

| Phase | Status | Completion Date | Notes |
|-------|--------|-----------------|-------|
| 1: Reproducibility | 🟢 Complete | ___________ | Lock files in git |
| 2: Standardization | 🟢 Complete | ___________ | All modules validated |
| 3: K8s Pinning | 🟢 Complete | ___________ | Versions documented |
| 4: Cluster Upgrades | 🟢 Complete | ___________ | All clusters at 1.34.0 |
| 5: Long-term | 🔵 Ongoing | — | Quarterly reviews |

### Final Approval
- **Project Owner:** ___________ **Date:** ___________
- **Infrastructure Lead:** ___________ **Date:** ___________
- **Engineering Manager:** ___________ **Date:** ___________

---

## Notes & Issues Tracker

| Issue | Severity | Status | Resolution | Date |
|-------|----------|--------|-----------|------|
| | | | | |
| | | | | |
| | | | | |

---

## Reference Documents

- 📄 [INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md) - Full technical plan
- 📄 [VERSIONS.md](VERSIONS.md) - Current version inventory
- 📄 [AUDIT_FINDINGS.txt](AUDIT_FINDINGS.txt) - Initial audit report
- 📄 [KUBERNETES_VERSION_POLICY.md](docs/KUBERNETES_VERSION_POLICY.md) - K8s versioning policy

