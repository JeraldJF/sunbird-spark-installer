# Infrastructure Upgrade Priority Guide

**Based on:** VERSIONS.md analysis
**Focus:** What can be upgraded, what breaks things, what requires new infrastructure
**Current State:** Kubernetes 1.33.6 (AKS), providers not pinned

---

## Executive Summary

| Component | Current | Latest | Can Upgrade? | Breaks? | Requires New Infra? |
|-----------|---------|--------|--------------|---------|---------------------|
| **Kubernetes (AKS)** | 1.33.6 | 1.35 | ✅ YES | ❌ NO | ❌ NO (rolling upgrade) |
| **Azure Provider** | ~> 4.0 | 4.63 | ✅ YES | ❌ NO | ❌ NO (safe) |
| **Google Provider** | ~> 5.0 | 5.x | ✅ YES | ❌ NO | ❌ NO (safe) |
| **Terraform/OpenTofu** | Uncontrolled | 1.14.7 | ⚠️ LOCAL ONLY | ❌ NO | ❌ NO (your machine) |

**Bottom Line:** Everything can be upgraded on existing infrastructure without breaking anything.

---

## Part 1: Current vs Latest Versions (from VERSIONS.md)

### Kubernetes

| Provider | Current | Latest | Gap |
|----------|---------|--------|-----|
| AKS (Azure) | 1.33.6 (auto-selected) | 1.35 | 2 versions behind |
| GKE (GCP) | Not pinned (unknown) | 1.35 | Unknown |

### Terraform Providers

| Provider | Current Constraint | Latest Version | Status |
|----------|-------------------|-----------------|--------|
| azurerm | ~> 4.0 | 4.63 | 0.63 behind |
| google | ~> 5.0 | 5.x | Compatible |
| tls | Not defined | 4.x | Missing constraint |
| local | ~> 2.5 | 2.5.x | Compatible |
| random | ~> 3.6 | 3.6.x | Compatible |
| null | ~> 3.2 | 3.2.x | Compatible |

### Terraform/OpenTofu Binary

| Component | Current | Latest | Notes |
|-----------|---------|--------|-------|
| OpenTofu | Uncontrolled (system default) | 1.14.7 | Depends on who runs it from their machine |

---

## Part 2: Upgrade Sequence (Order Matters)

```
STEP 1: Pin Provider Versions (Phase 1 - SAFE, DO FIRST)
   └─ Add version constraints to code
   └─ Remove -upgrade flags
   └─ Lock providers in place
   └─ NO INFRASTRUCTURE CHANGE
   └─ Risk: 🟢 NONE

STEP 2: Upgrade Azure Provider 4.0 → 4.63 (Phase 2 - SAFE)
   └─ Update constraint: ~> 4.0 → latest 4.63
   └─ Can be done on running cluster
   └─ No breaking changes in 4.x
   └─ Risk: 🟢 LOW

STEP 3: Upgrade Kubernetes 1.33.6 → 1.34.0 (Phase 3 - MEDIUM RISK)
   └─ Minor version upgrade
   └─ Requires rolling cluster update (30-60 min)
   └─ NO DOWNTIME (pods migrate automatically)
   └─ Test on dev first
   └─ Risk: 🟠 MEDIUM (but safe)

STEP 4: Upgrade Kubernetes 1.34.0 → 1.35 (Phase 4 - FUTURE)
   └─ Wait 4-6 weeks after 1.34 stable
   └─ Same process as 1.33→1.34
   └─ Risk: 🟠 MEDIUM
```

**WHY THIS ORDER?**
1. Step 1 must be first (enables reproducibility)
2. Step 2 can happen anytime after Step 1 (provider doesn't affect K8s)
3. Step 3 requires Steps 1-2 complete (ensures stability)
4. Step 4 happens 4-6 weeks after Step 3 (proven stability)

---

## Part 3: Detailed Upgrade Analysis

### STEP 1: Pin Provider Versions (SAFE on Existing Cluster)

**What:** Add version constraints to terraform code
**Risk:** 🟢 NONE
**Breaks Existing Infra:** ❌ NO
**Requires New Cluster:** ❌ NO
**Timeline:** 30 minutes
**When:** TODAY

**What Happens:**
```
Before:
  tofu init -upgrade  → Fetches LATEST provider (unpredictable)

After:
  tofu init           → Uses locked versions (reproducible)
  Result: Same infrastructure every time
```

**How:**
```
Files to modify:
  1. opentofu/azure/template/main.tf         (CREATE)
  2. opentofu/gcp/template/main.tf           (CREATE)
  3. opentofu/azure/template/install.sh      (remove -upgrade)
  4. opentofu/gcp/template/install.sh        (remove -upgrade)

Impact on running cluster: ZERO
Data loss: NO
Downtime: NO
```

---

### STEP 2: Upgrade Azure Provider to Latest 4.x (SAFE on Existing Cluster)

**What:** Update azure provider from ~> 4.0 to latest (4.63)
**Current:** ~> 4.0 (uses whatever 4.x is latest)
**Latest:** 4.63 (released and stable)
**Risk:** 🟢 LOW
**Breaks Existing Infra:** ❌ NO
**Requires New Cluster:** ❌ NO
**Timeline:** 1 hour (including testing)
**When:** After Step 1 is stable (1-2 weeks)

**What Happens:**
```
Before:  provider ~> 4.0 (could be 4.0, 4.20, 4.63)
After:   provider ~> 4.0 (locked to 4.63 via lock file)

Why safe:
  ✓ All 4.x versions are compatible
  ✓ No breaking changes within 4.x
  ✓ Only patch/minor improvements
  ✓ Existing infrastructure doesn't change
```

**Impact:**
- ✅ Provider features updated
- ✅ Bug fixes applied
- ✅ No cluster recreation
- ✅ No workload changes
- ✅ No data loss

---

### STEP 3: Upgrade Kubernetes 1.33.6 → 1.34.0 (MEDIUM RISK but SAFE)

**What:** Upgrade cluster Kubernetes version
**Current:** 1.33.6
**Next:** 1.34.0 (minor version)
**Risk:** 🟠 MEDIUM
**Breaks Existing Infra:** ❌ NO (backward compatible)
**Requires New Cluster:** ❌ NO (rolling upgrade on same cluster)
**Timeline:** 2-4 hours per environment (dev, staging, prod)
**When:** After Step 1-2 stable (2-4 weeks)

**What Happens:**
```
Rolling Upgrade Process:
  1. Master nodes update first (no workload impact)
  2. Worker nodes update one at a time
  3. Pods automatically migrate to nodes not being updated
  4. Total time: 30-60 minutes per cluster
  5. Zero application downtime
  6. Data is preserved

Why it's safe:
  ✓ 1.33→1.34 is minor version (backward compatible)
  ✓ Rolling upgrade ensures pods keep running
  ✓ Velero backup available for rollback
  ✓ Test on dev first (proven safe)
```

**Process:**
```
Step 3a: Upgrade Dev Cluster
  1. Update terraform.tfvars: kubernetes_version = "1.34.0"
  2. Run: tofu plan (review changes)
  3. Run: tofu apply (upgrade happens)
  4. Monitor: Wait 30-60 minutes
  5. Validate: All pods running, no errors
  6. Approve: Ready for staging

Step 3b: Wait & Monitor
  1. Leave dev on 1.34.0 for 1-2 weeks
  2. Monitor for any issues
  3. Collect feedback from team
  4. If stable, proceed to staging

Step 3c: Upgrade Staging Cluster
  1. Same process as dev
  2. Shorter validation (8-12 hours, not 1-2 weeks)
  3. Parallel testing before production

Step 3d: Upgrade Production Cluster
  1. Schedule during maintenance window
  2. Same process as staging
  3. Extended monitoring (24+ hours)
  4. Stakeholder approval
```

**Impact:**
- ✅ New K8s features available
- ✅ Security patches applied
- ✅ API improvements
- ✅ No data loss
- ✅ No app downtime
- ⚠️ Transient pod migration (invisible to users)

---

### STEP 4: Upgrade Kubernetes 1.34.0 → 1.35 (FUTURE - 4-6 weeks later)

**What:** Upgrade cluster to latest Kubernetes
**Current:** 1.34.0 (after Step 3)
**Latest:** 1.35
**Risk:** 🟠 MEDIUM
**Breaks Existing Infra:** ❌ NO (backward compatible)
**Requires New Cluster:** ❌ NO (rolling upgrade)
**Timeline:** 2-4 hours per environment
**When:** 4-6 weeks after Step 3 is stable

**Process:** Same as Step 3 (rolling upgrade)

---

## Part 4: What Cannot Be Upgraded On Existing Cluster

### Azure Provider Major Version (4.0 → 5.0)

**Status:** 🔴 BREAKING - Requires new cluster (future planning)
**Why:** Major version jump has breaking changes
**Timeline:** Plan for Q3-Q4 2026 (6+ months from now)
**Process:** New cluster required
**Action Required:** Plan separately when 5.0 released

### Google Provider Major Version (5.0 → 6.0)

**Status:** 🔴 BREAKING - Requires new cluster (future planning)
**Why:** Major version jump has breaking changes
**Timeline:** Plan when released (unknown)
**Process:** New cluster required

### Terraform/OpenTofu Major Version (1.x → 2.0)

**Status:** 🔴 NOT YOUR PROBLEM - Depends on person running it
**Why:** Different people may have different local versions
**Solution:** Pin in code with `required_version = ">= 1.8.0, < 2.0"`
**Action:** Already handled in Step 1

---

## Part 5: Quick Decision Matrix

**Can I upgrade this on my running cluster?**

```
Kubernetes Minor Version (1.33 → 1.34)?
  → YES, rolling upgrade, no downtime, no data loss

Kubernetes Patch Version (1.33.6 → 1.33.7)?
  → YES, same process as minor (when available)

Azure Provider patch (4.20 → 4.63)?
  → YES, no cluster changes, safe

Azure Provider major (4.0 → 5.0)?
  → NO, requires new cluster (future)

Google Provider patch (5.0 → 5.1)?
  → YES, no cluster changes, safe

Google Provider major (5.0 → 6.0)?
  → NO, requires new cluster (future)

Terraform version?
  → LOCAL ONLY, depends on who runs it

Helm chart versions?
  → YES, independent of infrastructure
```

---

## Part 6: Timeline Summary

```
IMMEDIATE (Today)
  ├─ Step 1: Pin provider versions (30 min)
  └─ No cluster changes

WEEK 1-2
  ├─ Step 1 validation in production
  └─ Monitor for any issues

WEEK 2-4
  ├─ Step 2: Upgrade Azure provider (safe)
  └─ Dev → Staging → Production

WEEK 4-6
  ├─ Step 3: Upgrade K8s 1.33 → 1.34
  ├─ Dev cluster upgrade (2 hours)
  ├─ Validate 1-2 weeks
  ├─ Staging upgrade (2 hours)
  └─ Production upgrade (2 hours)

WEEK 10+
  ├─ Step 4: Upgrade K8s 1.34 → 1.35 (future)
  └─ Same process as Step 3

Q3-Q4 2026
  └─ Plan major version upgrades (5.0, 6.0, etc.)
```

---

## Part 7: Rollback Plan

**If something breaks:**

### Rollback Kubernetes
```bash
# If 1.33.6 → 1.34 causes issues:
1. Edit terraform.tfvars: kubernetes_version = "1.33.6"
2. Run: tofu apply
3. Wait 30-60 minutes for downgrade
4. Verify: kubectl version
```

### Rollback Provider Version
```bash
# If azure provider 4.63 causes issues:
1. Edit constraint: version = "~> 4.0"
2. Run: tofu init (uses older version from range)
3. Run: tofu apply
```

### Restore from Backup
```bash
# If data corruption:
1. Velero backup available
2. Restore from pre-upgrade snapshot
3. No data loss
```

---

## Summary Table: What to Do

| Component | Current | Target | Action | Risk | Timeline |
|-----------|---------|--------|--------|------|----------|
| **Azure Provider** | ~> 4.0 | 4.63 (latest 4.x) | Pin version | 🟢 LOW | Now |
| **Google Provider** | ~> 5.0 | 5.x (latest) | Pin version | 🟢 LOW | Now |
| **K8s (minor)** | 1.33.6 | 1.34.0 | Rolling upgrade | 🟠 MED | Week 4+ |
| **K8s (future)** | 1.34.0 | 1.35 | Rolling upgrade | 🟠 MED | Week 10+ |
| **Major versions** | — | — | Plan new infra | 🔴 HIGH | Q3-Q4 2026 |

---

## Key Points

✅ **All minor/patch upgrades safe on existing cluster**
❌ **Major version upgrades require new cluster**
⚠️ **Test on dev first, always**
🔄 **Rolling upgrades = no downtime**
💾 **Velero backups available for rollback**
📋 **Pin versions in code for reproducibility**

