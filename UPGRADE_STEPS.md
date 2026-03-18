# Step-by-Step Upgrade Guide

**Follows:** UPGRADE_PRIORITY_GUIDE.md sequence
**Focus:** Exact commands and verification steps for each upgrade
**Current State:** Kubernetes 1.33.6, providers not pinned

---

## STEP 1: Pin Provider Versions (DO THIS FIRST - 30 minutes)

### Why This Step First?
- Ensures reproducible deployments
- Locks provider versions
- No infrastructure changes
- Safe to do immediately
- Required before other upgrades

### File 1: Create `opentofu/azure/template/main.tf`

```bash
# Create the file
cat > opentofu/azure/template/main.tf << 'EOF'
terraform {
  required_version = ">= 1.8.0, < 2.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {}
}
EOF
```

### File 2: Create `opentofu/gcp/template/main.tf`

```bash
# Create the file
cat > opentofu/gcp/template/main.tf << 'EOF'
terraform {
  required_version = ">= 1.8.0, < 2.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "gcs" {}
}
EOF
```

### File 3: Remove `-upgrade` from `opentofu/azure/template/install.sh`

```bash
# Find this line:
tofu init -upgrade

# Replace with:
tofu init
```

### File 4: Remove `-upgrade` from `opentofu/gcp/template/install.sh`

```bash
# Find this line:
tofu init -upgrade

# Replace with:
tofu init
```

### Verify Step 1

```bash
# Test Azure setup
cd opentofu/azure/template
tofu init

# Expected output:
# Terraform has been successfully configured!

# Test GCP setup
cd opentofu/gcp/template
tofu init

# Expected output:
# Terraform has been successfully configured!

# Check lock files were created
ls -la opentofu/azure/template/.opentofu.lock.hcl
ls -la opentofu/gcp/template/.opentofu.lock.hcl

# Should show files exist

# Check what versions are locked
grep "version" opentofu/azure/template/.opentofu.lock.hcl | head -3
grep "version" opentofu/gcp/template/.opentofu.lock.hcl | head -3

# Should show pinned versions like: "version" = "4.32.0"
```

### Commit Step 1

```bash
git add opentofu/azure/template/main.tf
git add opentofu/gcp/template/main.tf
git add opentofu/azure/template/.opentofu.lock.hcl
git add opentofu/gcp/template/.opentofu.lock.hcl
git add opentofu/azure/template/install.sh
git add opentofu/gcp/template/install.sh

git commit -m "Step 1: Pin provider versions for reproducibility"
git push
```

### ✅ Step 1 Complete

- [x] Both main.tf files created
- [x] -upgrade flags removed
- [x] Lock files generated
- [x] tofu init runs successfully
- [x] Changes committed

**No infrastructure changes. Your cluster is unchanged.**

---

## STEP 2: Upgrade Azure Provider to Latest 4.x (1-2 weeks after Step 1)

### Why After Step 1?
- Step 1 must be proven stable in production first
- Ensures reproducibility before making changes
- Allows team to understand new version control

### Prerequisites
- [ ] Step 1 completed and stable (1-2 weeks)
- [ ] No issues reported in production
- [ ] Team familiar with lock files

### What Happens
Provider version updates from whatever 4.x is currently locked to latest 4.63.
The lock file will download latest compatible provider.

### Command

```bash
# This is automatic - just run tofu init again
# After Step 1 is stable, go to any Azure environment:

cd opentofu/azure/dev

# This will fetch latest provider satisfying ~> 4.0 (which is 4.63)
tofu init

# Update lock file
git add opentofu/azure/template/.opentofu.lock.hcl
git commit -m "Step 2: Update Azure provider to latest 4.x"
git push
```

### Verify Step 2

```bash
# Check what version was downloaded
grep -A 5 "hashicorp/azurerm" opentofu/azure/template/.opentofu.lock.hcl | grep version

# Should show: "version" = "4.63.0" (or latest 4.x)

# Dry-run to see if any changes would happen
cd opentofu/azure/dev
tofu plan

# Should show: "No changes. Your infrastructure matches the configuration."
```

### ✅ Step 2 Complete

- [x] tofu init run successfully
- [x] Lock file updated to latest 4.x provider
- [x] tofu plan shows no infrastructure changes
- [x] Changes committed

**No infrastructure changes. Provider is now reproducible.**

---

## STEP 3: Upgrade Kubernetes 1.33.6 → 1.34.0 (Week 4+)

### Prerequisites
- [ ] Step 1 & 2 completed and proven stable (2-4 weeks)
- [ ] Maintenance window scheduled
- [ ] Velero backup verified working
- [ ] Team ready

### Why 4+ weeks after?
- Ensure Step 1-2 are stable
- Build confidence in new process
- Test thoroughly on dev
- Allow rollback preparation

### Timeline Per Environment

```
Dev:        30-60 minutes upgrade + 24 hours validation
Staging:    30-60 minutes upgrade + 8-12 hours validation
Production: 30-60 minutes upgrade + 24+ hours monitoring
```

### 3a: DEV CLUSTER UPGRADE

**Step 3a-1: Plan the Upgrade**

```bash
cd opentofu/azure/dev

# Edit terraform.tfvars
# Find: kubernetes_version = "1.33.6"
# Change to: kubernetes_version = "1.34.0"

# Review what will change
tofu plan

# Expected output:
# azurerm_kubernetes_cluster.main will be updated:
#   kubernetes_version: "1.33.6" → "1.34.0"
# No other changes
```

**Step 3a-2: Apply the Upgrade**

```bash
cd opentofu/azure/dev

# Apply the change
tofu apply

# Watch the progress in Azure portal
# Master nodes update first (no workload impact)
# Then worker nodes one by one (pods migrate automatically)
# Total time: 30-60 minutes
```

**Step 3a-3: Verify Immediately**

```bash
# Check K8s version
kubectl version --short

# Output should show:
# Server: v1.34.0

# Check all nodes updated
kubectl get nodes -o wide

# Output should show all nodes with 1.34.0

# Check all pods running
kubectl get pods -A

# Output should show all pods in Running state
```

**Step 3a-4: Validate for 24 Hours**

```bash
# Hour 0-1: Basic checks
  kubectl get pods -A
  kubectl logs -n <namespace> <pod>  # Check for errors
  kubectl get svc -A                   # Services responding

# Hour 1-4: Application testing
  # Login to application
  # Create test resources
  # Verify database connectivity
  # Check Flink jobs processing

# Hour 4-24: Monitor
  # Check Prometheus metrics
  # Watch Grafana dashboards
  # Look for unusual errors
  # No restart loops
  # No resource exhaustion
```

**Step 3a-5: Get Dev Approval**

```bash
# After 24 hours of stability:
# [ ] All pods running
# [ ] No error spikes
# [ ] Applications functional
# [ ] Ready for staging

# If issues found, rollback:
cd opentofu/azure/dev
# Edit terraform.tfvars: kubernetes_version = "1.33.6"
tofu apply
# Wait 30-60 minutes
```

### 3b: WAIT & MONITOR

```
Dev cluster on 1.34.0 for 1-2 weeks

Watch for:
  ✓ Sustained stability
  ✓ No memory leaks
  ✓ No CPU spikes
  ✓ No database issues
  ✓ No application errors

If all good → proceed to staging
If issues → rollback and investigate
```

### 3c: STAGING CLUSTER UPGRADE

```bash
# Same process as dev:

cd opentofu/azure/staging

# Edit terraform.tfvars:
# kubernetes_version = "1.34.0"

tofu plan
tofu apply

# Monitor for 8-12 hours (shorter than dev, already proven)
# Check: pods, errors, metrics

# If stable → approve for production
```

### 3d: PRODUCTION CLUSTER UPGRADE

```bash
# CRITICAL: Schedule maintenance window

cd opentofu/azure/production

# STEP 1: Backup
# Verify Velero backup:
velero backup get
# Should show recent backup

# STEP 2: Plan
# Edit terraform.tfvars:
# kubernetes_version = "1.34.0"

tofu plan

# Review output carefully

# STEP 3: Get Approval
# [ ] Security team approved
# [ ] Engineering manager approved
# [ ] On-call engineer ready
# [ ] Rollback plan understood

# STEP 4: Apply (DURING MAINTENANCE WINDOW)
# Open dashboards before starting:
#   - Prometheus
#   - Grafana
#   - Azure portal
#   - Application monitoring

tofu apply

# WATCH CONTINUOUSLY
# Do not leave until:
#   - All nodes upgraded (30-60 min)
#   - All pods running (5-10 min after)
#   - All services responding (5-10 min)

# STEP 5: Immediate Verification
kubectl version --short          # Should show 1.34.0
kubectl get nodes -o wide        # All at 1.34.0
kubectl get pods -A              # All running
kubectl get svc -A               # Services up

# STEP 6: Extended Monitoring (24+ hours)
# Watch metrics for abnormalities:
#   - CPU usage
#   - Memory usage
#   - Network I/O
#   - Error rates
#   - User reports

# STEP 7: Stakeholder Sign-Off
# [ ] Team satisfied
# [ ] No escalations
# [ ] Ready to declare success
```

### Verify Step 3

**All Three Clusters:**

```bash
# Check all clusters on 1.34.0
# Dev:
kubectl --context=dev version --short    # v1.34.0

# Staging:
kubectl --context=staging version --short  # v1.34.0

# Production:
kubectl --context=prod version --short   # v1.34.0

# All should match
```

### ✅ Step 3 Complete

- [x] Dev cluster: 1.33.6 → 1.34.0 ✅ (24 hrs stable)
- [x] Staging cluster: 1.33.6 → 1.34.0 ✅ (8-12 hrs stable)
- [x] Production cluster: 1.33.6 → 1.34.0 ✅ (24+ hrs stable)
- [x] All workloads running
- [x] No data loss
- [x] Zero downtime achieved
- [x] terraform.tfvars updated in all envs

**Kubernetes upgraded successfully. Rolling upgrade complete.**

---

## STEP 4: Upgrade Kubernetes 1.34.0 → 1.35 (Week 10+)

### When
- 4-6 weeks after Step 3 is proven stable
- When 1.35 is widely adopted
- Following same process as Step 3

### Process
Identical to Step 3:
1. Dev cluster first (30-60 min + 24 hrs validation)
2. Wait 1-2 weeks
3. Staging cluster (30-60 min + 8-12 hrs validation)
4. Production cluster (30-60 min + 24+ hrs validation)

### Commands

```bash
# Only change:
# kubernetes_version = "1.34.0" → "1.35.0"

# Everything else same as Step 3

cd opentofu/azure/dev
# Edit terraform.tfvars
tofu plan
tofu apply

# Monitor → Staging → Production (same sequence)
```

---

## ROLLBACK PROCEDURES

### If Step 1 Breaks

```bash
git revert <commit-hash>
git push

# No infrastructure impact
```

### If Provider Upgrade Breaks (Step 2)

```bash
cd opentofu/azure/dev

# Edit constraint:
# version = "~> 4.0"

tofu init   # Uses earlier version from range
tofu plan
tofu apply

# No infrastructure changes needed
```

### If Kubernetes Upgrade Breaks (Step 3)

```bash
cd opentofu/azure/dev

# Edit terraform.tfvars:
# kubernetes_version = "1.34.0" → "1.33.6"

tofu plan
# Review output

tofu apply

# Wait 30-60 minutes for downgrade
# Verify: kubectl version
```

### If Catastrophic Failure

```bash
# Velero restore available:
velero restore create --from-backup <backup-name>

# Restores entire cluster from backup
# No data loss
```

---

## Summary: 4 Step Process

| Step | What | Time | Risk | Timing |
|------|------|------|------|--------|
| **1** | Pin providers | 30 min | 🟢 NONE | TODAY |
| **2** | Update to latest 4.x | Automatic | 🟢 LOW | Week 1-2 |
| **3** | K8s 1.33 → 1.34 | 6 hours | 🟠 MED | Week 4+ |
| **4** | K8s 1.34 → 1.35 | 6 hours | 🟠 MED | Week 10+ |

---

## Checklist: Before You Start

- [ ] Read VERSIONS.md (current state)
- [ ] Read UPGRADE_PRIORITY_GUIDE.md (why each step)
- [ ] Read this file (exact commands)
- [ ] Backup verified (Velero)
- [ ] Team aware
- [ ] Rollback plan understood

