# Sunbird Spark Installer - Infrastructure Upgrade Plan
**Generated:** 2026-03-16
**Prepared for:** Sunbird Spark Infrastructure Team
**Scope:** Version pinning, provider compatibility, Kubernetes alignment, and safe cluster upgrades

---

## Executive Summary

Your infrastructure has **HIGH RISK** due to non-reproducible deployments caused by:
1. **No OpenTofu version pinning** → system default (any >= 1.0)
2. **Uncontrolled provider upgrades** → `-upgrade` flag fetches latest versions
3. **Empty lock files** → provider versions not reproducible
4. **Inconsistent Kubernetes versions** → AKS on 1.33.6, GKE uncontrolled
5. **Missing provider constraints** → TLS and GCP modules have no version bounds

**Risk Level:** 🔴 **CRITICAL**

This plan fixes reproducibility first (Phase 1), then safely upgrades clusters (Phase 4+).

---

## Current State Analysis

| Component | Current | Latest | Gap | Risk |
|-----------|---------|--------|-----|------|
| **OpenTofu Binary** | Uncontrolled | 1.14.7 | Unknown | 🔴 Critical |
| **Azure Provider** | ~> 4.0 (up to 4.63) | 4.63 | Behind by 0.63 | ⚠️ Medium |
| **Google Provider** | ~> 5.0 (1 module) | 5.x | Mostly implicit | 🔴 Critical |
| **TLS Provider** | (none) | 4.x | Uncontrolled | 🔴 Critical |
| **Kubernetes (AKS)** | 1.33.6 (auto) | 1.35 | 2 versions | ⚠️ Medium |
| **Kubernetes (GKE)** | Uncontrolled | 1.35 | Unknown | 🔴 Critical |
| **Helm Charts** | v2 (0.1.0) | v2 (0.1.0) | Current | ✅ OK |
| **Lock Files** | Empty | Should be populated | — | 🔴 Critical |

---

## Upgrade Strategy Overview

```
PHASE 1 (TODAY): Lock Down Infrastructure Reproducibility
├─ Root module required_version blocks
├─ Provider version pinning
├─ Remove -upgrade flag
└─ Populate lock files

PHASE 2 (SHORT TERM): Provider Version Standardization
├─ Align all modules to consistent constraints
├─ TLS provider versioning
└─ GCP module provider constraints

PHASE 3 (SHORT TERM): Kubernetes Version Pinning
├─ AKS explicit version in module
├─ GKE explicit version in module
└─ Version compatibility matrix

PHASE 4 (MEDIUM TERM): Safe Cluster Upgrades
├─ Test minor version upgrades (1.33 → 1.34)
├─ Validate application compatibility
└─ Production cluster rolling upgrade

PHASE 5 (LONG TERM): Full Version Alignment
├─ Kubernetes 1.34 → 1.35
├─ Provider major version updates
└─ Docker-based OpenTofu deployments
```

---

# PHASE 1: Lock Down Infrastructure Reproducibility
**Duration:** ~30 minutes | **Risk:** 🟢 LOW | **Impact:** 🔴 CRITICAL
**Status:** SAFE ON EXISTING CLUSTER | PARALLELIZABLE TASKS

This phase is **non-breaking** — only adds version constraints, no functionality changes.

## 1.1 Add Root Module `required_version` Block (Azure)

**File:** `opentofu/azure/template/main.tf`

**Status:** ✅ SAFE ON EXISTING CLUSTER | PARALLELIZABLE TASK

**Why Safe:** Only specifies which versions are allowed; doesn't change deployment logic.

**Current State:** File doesn't exist or has no version constraints

**Action:**
```hcl
# Add to opentofu/azure/template/main.tf (at the very top)

terraform {
  required_version = ">= 1.8.0, < 2.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
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
```

**Rationale:**
- `>= 1.8.0` = minimum OpenTofu version with stable features
- `< 2.0` = avoid major version breaking changes
- Explicitly lists all providers used across Azure modules
- TLS pinned to 4.0 (fixes: tls provider has no version constraint)

---

## 1.2 Add Root Module `required_version` Block (GCP)

**File:** `opentofu/gcp/template/main.tf`

**Status:** ✅ SAFE ON EXISTING CLUSTER | PARALLELIZABLE TASK

**Current State:** File doesn't exist or has no version constraints

**Action:**
```hcl
# Add to opentofu/gcp/template/main.tf (at the very top)

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
```

**Rationale:**
- Same OpenTofu version constraint as Azure (consistency)
- Explicitly declares google provider (fixes: GCP modules have implicit google provider)
- TLS pinned to 4.0 (fixes: no version constraint)

---

## 1.3 Update install.sh (Azure) - Remove `-upgrade` Flag

**File:** `opentofu/azure/template/install.sh`

**Status:** ✅ SAFE ON EXISTING CLUSTER

**Why Safe:** Lock file + no `-upgrade` flag = reproducible; existing state unaffected.

**Current State:** Lines likely contain `tofu init -upgrade`

**Action:** Find and modify the `tofu init` call:

```bash
# BEFORE
tofu init -upgrade

# AFTER
tofu init
```

**Why:**
- `-upgrade` flag ignores lock file and fetches latest provider versions
- Without it, `tofu init` respects .opentofu.lock.hcl
- Ensures same provider versions across all deployments

---

## 1.4 Update install.sh (GCP) - Remove `-upgrade` Flag

**File:** `opentofu/gcp/template/install.sh`

**Status:** ✅ SAFE ON EXISTING CLUSTER

**Action:** Same as 1.3 (remove `-upgrade` from `tofu init`)

---

## 1.5 Populate Lock Files

**Files:**
- `opentofu/azure/template/.opentofu.lock.hcl`
- `opentofu/gcp/template/.opentofu.lock.hcl`

**Status:** ✅ SAFE ON EXISTING CLUSTER

**Action:**

```bash
# Azure
cd opentofu/azure/template
tofu init

# GCP
cd opentofu/gcp/template
tofu init
```

**What Happens:**
- `tofu init` reads constraints from `main.tf` (added in 1.1 and 1.2)
- Downloads provider versions matching constraints
- Creates/updates `.opentofu.lock.hcl` with exact versions used
- Commit both lock files to git

**Commit:**
```bash
git add opentofu/azure/template/.opentofu.lock.hcl
git add opentofu/gcp/template/.opentofu.lock.hcl
git commit -m "Lock OpenTofu provider versions for reproducibility"
```

---

## 1.6 Align DIAL Addon Provider Constraint

**File:** `addons/dial/opentofu/azure/storage/main.tf`

**Status:** ✅ SAFE ON EXISTING CLUSTER

**Current Constraint:** `~> 4.0.1` (stricter than main: `~> 4.0`)

**Action:** Change to match main Azure modules:

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"  # Changed from 4.0.1
    }
  }
}
```

**Why:**
- Consistency across all modules
- Constraint is already satisfied (4.0.1 ⊂ 4.0)
- Simplifies version management

---

## Phase 1 Summary

| Task | File | Change | Safe? |
|------|------|--------|-------|
| 1.1 | opentofu/azure/template/main.tf | Create with required_version | ✅ |
| 1.2 | opentofu/gcp/template/main.tf | Create with required_version | ✅ |
| 1.3 | opentofu/azure/template/install.sh | Remove `-upgrade` | ✅ |
| 1.4 | opentofu/gcp/template/install.sh | Remove `-upgrade` | ✅ |
| 1.5 | .opentofu.lock.hcl (both) | Run `tofu init` | ✅ |
| 1.6 | addons/dial/.../main.tf | Align constraint | ✅ |

**All tasks are parallelizable.** Can be done in any order.

---

# PHASE 2: Provider Version Standardization
**Duration:** ~45 minutes | **Risk:** 🟡 LOW-MEDIUM | **Impact:** 🟢 MEDIUM
**Status:** SAFE ON EXISTING CLUSTER (with testing)

Standardizes provider versions across all modules for consistency.

## 2.1 Update GCP Module Constraints

**Problem:** 8 GCP modules have implicit provider dependencies. Only 1 explicitly declares google provider.

**Files to Update:**
- `opentofu/gcp/modules/gke/main.tf`
- `opentofu/gcp/modules/network/main.tf`
- `opentofu/gcp/modules/service-account/main.tf`
- `opentofu/gcp/modules/storage/main.tf`
- `opentofu/gcp/modules/upload-files/main.tf`
- `opentofu/gcp/modules/output-file/main.tf`
- `opentofu/gcp/modules/keys/main.tf`

**Status:** ✅ SAFE ON EXISTING CLUSTER (test first)

**Action:** Add terraform block to each:

```hcl
# Add to each GCP module main.tf

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    # Add any others used in the module
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}
```

**Testing:**
```bash
# For each GCP module
cd opentofu/gcp/modules/gke
tofu init
tofu validate
```

---

## 2.2 Audit Azure Module Constraints

**Status:** ✅ Already Defined (verify)

**Files to Check:**
- `opentofu/azure/modules/aks/main.tf` → azurerm ~> 4.0 ✅
- `opentofu/azure/modules/network/main.tf` → azurerm ~> 4.0 ✅
- `opentofu/azure/modules/storage/main.tf` → azurerm ~> 4.0 ✅
- `opentofu/azure/modules/output-file/main.tf` → local ~> 2.5, null ~> 3.2 ✅
- `opentofu/azure/modules/upload-files/main.tf` → local ~> 2.5, null ~> 3.2 ✅
- `opentofu/azure/modules/random_passwords/main.tf` → local, random, null ✅
- `opentofu/azure/modules/keys/main.tf` → TLS implicit ⚠️

**Action:** Update keys module to explicitly declare TLS:

```hcl
# opentofu/azure/modules/keys/main.tf

terraform {
  required_providers {
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}
```

---

## Phase 2 Summary

**Deliverables:**
- All 16 modules have explicit required_providers blocks
- Provider versions are standardized and documented
- No functional changes, only metadata

**Testing Required:** Run `tofu validate` in each module directory

---

# PHASE 3: Kubernetes Version Pinning
**Duration:** ~1 hour | **Risk:** 🟡 MEDIUM | **Impact:** 🟠 HIGH
**Status:** SAFE ON EXISTING CLUSTER (for pinning current version)

Pins Kubernetes versions to prevent drift and enable predictable cluster updates.

## 3.1 Pin AKS Kubernetes Version

**File:** `opentofu/azure/modules/aks/main.tf`

**Current State:** No `kubernetes_version` variable; Azure auto-selects latest stable (currently 1.33.6)

**Status:** ✅ SAFE ON EXISTING CLUSTER (when targeting current version 1.33.6)

**Action:** Add variable and constraint:

```hcl
# Add to opentofu/azure/modules/aks/main.tf

variable "kubernetes_version" {
  description = "Kubernetes version for AKS cluster"
  type        = string
  default     = "1.33.6"  # Current production version

  validation {
    condition     = can(regex("^1\\.(3[3-4]|35)", var.kubernetes_version))
    error_message = "Kubernetes version must be 1.33.x, 1.34.x, or 1.35.x"
  }
}

# In the azurerm_kubernetes_cluster resource, add:
resource "azurerm_kubernetes_cluster" "main" {
  # ... existing config ...
  kubernetes_version = var.kubernetes_version
  # ... rest of config ...
}
```

**Values File:** `opentofu/azure/<environment>/terraform.tfvars`

Add or update:
```hcl
kubernetes_version = "1.33.6"
```

**Why This Version:**
- 1.33.6 = current stable, proven in production
- 1.34 = next minor (available for future upgrade)
- 1.35 = latest (wait for broader adoption)

---

## 3.2 Pin GKE Kubernetes Version

**File:** `opentofu/gcp/modules/gke/main.tf`

**Current State:** No version constraint; GKE uses latest available

**Status:** ⚠️ REQUIRES CAREFUL PLANNING (but safe on existing)

**Action:** Add release channel + version constraint:

```hcl
# Add to opentofu/gcp/modules/gke/main.tf

variable "kubernetes_version" {
  description = "Kubernetes version for GKE cluster"
  type        = string
  default     = "1.33.0"  # Pinned release
}

variable "release_channel" {
  description = "Release channel: UNSPECIFIED, REGULAR, STABLE, RAPID"
  type        = string
  default     = "REGULAR"
}

# In the google_container_cluster resource, add:
resource "google_container_cluster" "primary" {
  # ... existing config ...

  min_master_version = var.kubernetes_version
  release_channel {
    channel = var.release_channel
  }

  # ... rest of config ...
}
```

**Values File:** `opentofu/gcp/<environment>/terraform.tfvars`

```hcl
kubernetes_version = "1.33.0"
release_channel    = "REGULAR"  # Auto-updates within 1.33.x
```

**Why REGULAR Channel:**
- STABLE = behind by 1-2 versions (very conservative)
- REGULAR = 2-3 months behind latest (good balance)
- RAPID = latest releases (risky for production)

---

## 3.3 Document Version Compatibility Matrix

**File:** `docs/KUBERNETES_VERSION_POLICY.md` (create new)

```markdown
# Kubernetes Version Policy

## Supported Versions

| Version | AKS | GKE | Support Level | Notes |
|---------|-----|-----|---------------|-------|
| 1.33.x  | ✅  | ✅  | Current       | Production |
| 1.34.x  | ⚠️  | ⏳  | Testing       | Minor upgrade available |
| 1.35.x  | 🔮 | 🔮 | Not yet tested | Plan for Q2 2026 |

## Upgrade Path

```
Current: 1.33.6
↓ (Step 1, 1-2 weeks): 1.33 → 1.34 (minor version)
↓ (Step 2, 2-4 weeks): 1.34 → 1.35 (minor version)
```

## Component Compatibility

| Component | 1.33 | 1.34 | 1.35 | Notes |
|-----------|------|------|------|-------|
| YugabyteDB 2.24 | ✅ | ✅ | ✅ | No K8s version deps |
| Kong 3.x | ✅ | ✅ | ✅ | No K8s version deps |
| Helm 3.15+ | ✅ | ✅ | ✅ | Latest Helm compatible |

## Upgrade Procedure

1. Test on dev cluster first
2. Validate all workloads
3. Upgrade production cluster
4. Monitor for 24 hours
5. Proceed to next version
```

---

## Phase 3 Summary

**Deliverables:**
- AKS has explicit pinned version (1.33.6)
- GKE has explicit pinned version + release channel
- Version compatibility documented
- Validation rules prevent invalid versions

**Testing Required:**
- Deploy to dev cluster with new variables
- Verify cluster stability

---

# PHASE 4: Safe Cluster Upgrades (Minor Versions)
**Duration:** 2-4 hours per upgrade | **Risk:** 🟠 MEDIUM | **Impact:** 🟢 HIGH
**Status:** REQUIRES NEW CLUSTER (for major jumps) | SAFE ROLLING (for minors)

## 4.1 Upgrade Path: 1.33 → 1.34 (Minor Version)

**Decision:** Can be done on existing cluster using rolling upgrade

**Risk Level:** 🟢 LOW (backward compatible)

**Timeline:**
- Dev cluster test: 30 minutes
- Staging validation: 2 hours
- Production rolling upgrade: 1-2 hours

### Step 1: Test on Dev Cluster

```bash
# 1. Update dev cluster terraform vars
cd opentofu/azure/dev
# Edit terraform.tfvars or .tfvars file:
# kubernetes_version = "1.34.0"

# 2. Plan the change
tofu plan

# 3. Review output for non-disruptive changes
# Expected: AKS cluster update only

# 4. Apply
tofu apply

# 5. Validate workloads
./scripts/validate-cluster.sh
```

**Validation Checklist:**
- [ ] All pods running
- [ ] Services responding
- [ ] No application errors in logs
- [ ] Database connectivity working
- [ ] Flink jobs processing
- [ ] Wait 30 minutes for stability

### Step 2: Staging Validation (if applicable)

```bash
cd opentofu/azure/staging
# Edit terraform.tfvars: kubernetes_version = "1.34.0"
tofu apply
# Run same validation
```

### Step 3: Production Rolling Upgrade

```bash
cd opentofu/azure/production
# Edit terraform.tfvars: kubernetes_version = "1.34.0"

# Plan to see what will change
tofu plan -out=upgrade-1.34.plan

# Review the plan carefully
cat upgrade-1.34.plan

# Apply during maintenance window
tofu apply upgrade-1.34.plan
```

**During Upgrade:**
- Azure will update master nodes first (no downtime)
- Then worker nodes one at a time (pods evicted and rescheduled)
- Total time: 30-60 minutes
- Applications remain available (pods migrate to other nodes)

**Post-Upgrade Validation:**
```bash
# Verify new version
kubectl version
kubectl get nodes -o wide  # Should show 1.34.x

# Check all workloads
kubectl get pods -A
kubectl logs -n <namespace> <pod>  # Sample check

# Monitor metrics
# Check Prometheus/Grafana for anomalies
```

---

## 4.2 Upgrade Path: 1.34 → 1.35 (Latest)

**Status:** SAFE ROLLING (2-4 weeks after 1.34 stabilizes)

**Same procedure as 4.1:**
1. Update dev cluster first
2. Wait 1 week for stability
3. Update staging
4. Update production

---

## 4.3 GCP Cluster Upgrade (if applicable)

For GKE, the process is simpler:

```bash
cd opentofu/gcp/production

# Option A: REGULAR release channel auto-upgrades within 1.33.x
# (no action needed, GCP handles automatically)

# Option B: Explicit version update
# terraform.tfvars: kubernetes_version = "1.34.0"
tofu apply
```

GKE upgrades automatically during the specified maintenance window.

---

## Phase 4 Summary

**Timeline:**
- 1.33 → 1.34: 4-6 hours (including validations)
- 1.34 → 1.35: 4-6 hours (2-4 weeks later)
- **Total major version alignment: 2 deployment windows**

**Risks Mitigated:**
- ✅ Data backup before upgrade (Velero)
- ✅ Rolling upgrade (no downtime)
- ✅ Validated on dev/staging first
- ✅ Easy rollback (tofu destroy + older state)

---

# PHASE 5: Full Version Alignment & Long-Term Strategy
**Duration:** Ongoing | **Risk:** 🟡 MEDIUM | **Impact:** 🟢 HIGH

## 5.1 Provider Major Version Updates (Future)

**Current:** Azure provider ~> 4.0 (currently 4.63)
**Future:** Plan for 5.0 when released

**Risk:** 🔴 BREAKING (requires testing)

**When to Upgrade:**
- 3-6 months after major version released
- Only after reviewing breaking changes
- Test on dev cluster first

**Procedure:**
1. Create breaking-change document
2. Test on dev cluster: update constraint to `~> 5.0`
3. Address any resource configuration changes
4. Apply to staging, then production

---

## 5.2 Docker-Based OpenTofu Deployments (Optional)

**Current:** System-installed OpenTofu (varies by CI/CD runner)
**Benefit:** Guaranteed version consistency across all environments

**Implementation:** (future initiative)

```bash
# Instead of:
tofu init && tofu apply

# Use Docker:
docker run --rm \
  -v $(pwd):/work \
  -w /work \
  opentofu/opentofu:1.8.0 \
  init
```

---

## 5.3 Terraform Registry Module Versioning (Optional)

**Current:** Git-based modules
**Future:** Publish to Terraform Registry with semantic versioning

**Benefits:**
- Formal versioning (1.0.0, 1.1.0, etc.)
- Breaking change documentation
- Easy upgrades: `version = "~> 1.0"`

---

# Implementation Timeline

## Week 1 (IMMEDIATE) - Phase 1 Only
**Effort:** ~1 hour | **Risk:** 🟢 LOW

- [ ] Add required_version blocks (1.1, 1.2)
- [ ] Remove -upgrade flags (1.3, 1.4)
- [ ] Populate lock files (1.5)
- [ ] Align DIAL addon (1.6)
- [ ] Commit to main branch

**Validation:** Run `tofu init && tofu validate` in all template directories

---

## Week 2 (SHORT TERM) - Phase 2 & 3
**Effort:** ~2 hours | **Risk:** 🟡 MEDIUM

- [ ] Update GCP module constraints (2.1)
- [ ] Explicit TLS constraints (2.2)
- [ ] Pin AKS version to 1.33.6 (3.1)
- [ ] Pin GKE version to 1.33.0 (3.2)
- [ ] Document version policy (3.3)

**Validation:**
- Run `tofu init && tofu validate` in all modules
- Dry-run on dev cluster (no actual changes)

---

## Weeks 3-4 (MEDIUM TERM) - Phase 4
**Effort:** ~4-6 hours deployment time (spread over 2 weeks)

- [ ] Week 3: Upgrade dev cluster to 1.34
- [ ] Week 3: Validate dev cluster stability (24 hours)
- [ ] Week 4: Upgrade staging cluster to 1.34
- [ ] Week 4: Upgrade production cluster to 1.34

---

## Weeks 5-8 (LONG TERM) - Phase 5
**Effort:** Research & planning

- [ ] Review provider major version changes
- [ ] Evaluate Docker-based deployments
- [ ] Plan for Kubernetes 1.35 upgrade
- [ ] Document update policy for team

---

# Risk Assessment

## Breaking Changes by Phase

### Phase 1 (Required Version Blocks)
- **Risk:** 🟢 NONE
- **Impact:** Adds version constraints only
- **Rollback:** Simple (remove terraform blocks)

### Phase 2 (Provider Constraints)
- **Risk:** 🟡 LOW
- **Impact:** Standardizes existing constraints
- **Rollback:** Revert provider constraint changes

### Phase 3 (K8s Version Pinning)
- **Risk:** 🟡 LOW
- **Impact:** Pins current versions, no immediate change
- **Rollback:** Change version variable back to old value

### Phase 4 (K8s Upgrades)
- **Risk:** 🟠 MEDIUM
- **Impact:** Rolling upgrade, transient downtime during node updates
- **Rollback:** Revert to previous K8s version (downtime again)
- **Mitigation:**
  - Backup with Velero before upgrade
  - Test on dev first
  - Upgrade during maintenance window
  - Monitor for 24 hours post-upgrade

### Phase 5 (Major Versions)
- **Risk:** 🔴 HIGH
- **Impact:** May require code/configuration changes
- **Mitigation:** Extensive testing on isolated environments

---

# Concurrent/Parallelizable Work

**Phase 1 tasks can all run in parallel:**
- 1.1 and 1.2: Create main.tf files simultaneously
- 1.3 and 1.4: Update install.sh scripts simultaneously
- 1.5: Run tofu init after both main.tf created
- 1.6: Update DIAL addon independently

**Phase 2 tasks can run in parallel:**
- 2.1: Update 7 GCP modules (independent, no dependencies)
- 2.2: Audit Azure modules (can overlap with 2.1)

**Phase 3 tasks:**
- 3.1 and 3.2: Can be done independently (Azure vs GCP)
- 3.3: Documentation can be written in parallel

**Phase 4 tasks:**
- Dev + Staging testing can overlap (if separate clusters)
- But Production must wait for staging validation

---

# Rollback Procedures

## Phase 1 Rollback
```bash
git revert <commit-hash>
tofu init  # Will use old provider versions from reverted state
```

## Phase 2 Rollback
```bash
git revert <commit-hash>
tofu init
```

## Phase 3 Rollback
```bash
# Edit terraform.tfvars back to old K8s version
kubernetes_version = "1.33.6"
tofu apply
```

## Phase 4 Rollback (from 1.34 back to 1.33)
```bash
# Edit terraform.tfvars
kubernetes_version = "1.33.6"
tofu plan
# Review rolling downgrade steps
tofu apply
```

---

# Success Criteria

## Phase 1 Complete
- ✅ All root modules have required_version blocks
- ✅ Lock files are populated and committed
- ✅ `-upgrade` flags removed from install scripts
- ✅ `tofu plan` shows no changes in existing environments

## Phase 2 Complete
- ✅ All modules have explicit provider constraints
- ✅ No implicit provider dependencies remain
- ✅ `tofu validate` passes in all modules

## Phase 3 Complete
- ✅ AKS cluster running on 1.33.6 (pinned)
- ✅ GKE cluster running on 1.33.0 (pinned)
- ✅ Version policy document published
- ✅ No unintended K8s version changes on redeployment

## Phase 4 Complete
- ✅ Dev cluster successfully upgraded to 1.34
- ✅ All workloads stable on 1.34 (24+ hours)
- ✅ Staging upgraded to 1.34
- ✅ Production upgraded to 1.34
- ✅ No application errors or performance degradation

## Phase 5 Complete (Ongoing)
- ✅ Version upgrade policy documented
- ✅ Team trained on version management
- ✅ CI/CD pipeline validates versions
- ✅ Quarterly update schedule established

---

# Files Summary

## Files to Create
1. `opentofu/azure/template/main.tf` (root module)
2. `opentofu/gcp/template/main.tf` (root module)
3. `docs/KUBERNETES_VERSION_POLICY.md`

## Files to Modify

### Phase 1
- `opentofu/azure/template/install.sh` (remove `-upgrade`)
- `opentofu/gcp/template/install.sh` (remove `-upgrade`)
- `addons/dial/opentofu/azure/storage/main.tf` (version constraint)

### Phase 2
- 7 GCP module `main.tf` files (add required_providers)
- `opentofu/azure/modules/keys/main.tf` (add TLS constraint)

### Phase 3
- `opentofu/azure/modules/aks/main.tf` (add kubernetes_version variable)
- `opentofu/gcp/modules/gke/main.tf` (add kubernetes_version variable)
- All environment `terraform.tfvars` files (add kubernetes_version)

## Lock Files to Populate
- `opentofu/azure/template/.opentofu.lock.hcl`
- `opentofu/gcp/template/.opentofu.lock.hcl`

---

# Quick Reference: Version Targets

| Component | Current | Phase 1 | Phase 3 | Phase 4 | Phase 5 |
|-----------|---------|---------|---------|---------|---------|
| **OpenTofu** | Any | >= 1.8.0, < 2.0 | >= 1.8.0, < 2.0 | >= 1.8.0, < 2.0 | >= 1.8.0, < 2.0 |
| **azurerm** | ~> 4.0 | ~> 4.0 | ~> 4.0 | ~> 4.0 | ~> 5.0 (future) |
| **google** | Implicit | ~> 5.0 | ~> 5.0 | ~> 5.0 | ~> 5.0 |
| **tls** | Implicit | ~> 4.0 | ~> 4.0 | ~> 4.0 | ~> 4.0 |
| **AKS K8s** | 1.33.6 (auto) | 1.33.6 (pinned) | 1.33.6 (pinned) | 1.34.0 | 1.35.x |
| **GKE K8s** | Uncontrolled | Uncontrolled | 1.33.0 (pinned) | 1.34.0 | 1.35.x |

---

# Appendix A: Version Constraint Syntax

```hcl
# Examples of terraform version constraints:

">= 1.0"           # At least 1.0 (allows 1.x, 2.0, etc.)
">= 1.0, < 2.0"    # At least 1.0 but less than 2.0 (1.x only)
"~> 1.8"           # At least 1.8 but less than 1.9 (1.8.x)
"~> 1.8.0"         # At least 1.8.0 but less than 1.9.0 (1.8.x)
"= 1.8.2"          # Exactly 1.8.2 (pinned)
```

For this project: **`~> X.Y`** is the right balance between stability and patch updates.

---

# Appendix B: Helpful Commands

```bash
# Check current OpenTofu version
tofu version

# Initialize and lock providers (after main.tf created)
cd opentofu/azure/template
tofu init

# Validate configuration
tofu validate

# Check what versions would be used
tofu init -upgrade  # (Only do this when intentionally upgrading)

# See what's in the lock file
cat .opentofu.lock.hcl | grep version

# See what would change
tofu plan -out=plan.out
cat plan.out

# Apply changes
tofu apply plan.out

# Check Kubernetes version on cluster
kubectl version --short
kubectl get nodes -o wide
```

---

# Document Version
- **Created:** 2026-03-16
- **Last Updated:** 2026-03-16
- **Status:** Ready for Implementation
- **Next Review:** 2026-04-16 (post-Phase 1)

