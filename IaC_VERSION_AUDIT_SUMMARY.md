# IaC Version Audit - Quick Summary

## 🎯 Key Question: "What version of OpenTofu/Terraform will run in production?"

### Answer: ❌ **UNKNOWN - UNCONTROLLED**

The system currently uses:
- **OpenTofu binary:** System-installed version (any >= 1.0)
- **Provider versions:** Latest satisfying constraints (due to `-upgrade` flag)
- **Lock status:** **NOT LOCKED** - reproducibility NOT guaranteed

---

## 📊 Quick Facts

| Metric | Status | Details |
|--------|--------|---------|
| **Total Modules** | 16 | 7 Azure + 8 GCP + 1 Addon |
| **Modules w/ Constraints** | 11/16 ✅ | But 5 missing constraints (GCP) |
| **OpenTofu Version Pinned** | ❌ | No `required_version` at root |
| **Provider Locks (populated)** | ❌ | Both lock files are EMPTY |
| **CI/CD Version Pinning** | ❌ | Bash script, no container isolation |
| **Risk Level** | 🔴 **HIGH** | Non-deterministic deployments |

---

## 🔍 What's Currently Defined

### Provider Constraints (Partial)

```
Azure (azurerm)          ✅ ~> 4.0, ~> 4.0.1
Google (google)          ⚠️ ~> 5.0 (1 module only, others implicit)
Utility (local)          ✅ ~> 2.5 (all 4 modules)
Utility (random)         ✅ ~> 3.6 (all 2 modules)
Utility (null)           ✅ ~> 3.2 (all 3 modules)
Utility (tls)            ❌ NO CONSTRAINT (latest always used)
```

### What's Missing

- ❌ **Root module terraform block** - No `required_version` defined
- ❌ **GCP provider constraints** - 5 modules use google/local implicitly
- ❌ **Lock files populated** - Both `.opentofu.lock.hcl` empty
- ❌ **CI/CD pinning** - No containerized OpenTofu version
- ❌ **Explicit tls constraint** - Latest version always used

---

## 🚨 Critical Issues

### 1. `-upgrade` Flag (HIGHEST PRIORITY)
**Location:** `opentofu/*/template/install.sh:23`

```bash
tofu init -upgrade        # ← This causes latest providers to be fetched
```

**Impact:** Each deployment pulls the latest provider version, ignoring lock files.

**Fix:** Remove `-upgrade` flag, use lock files instead.

---

### 2. Empty Lock Files
**Location:**
- `opentofu/azure/template/.opentofu.lock.hcl` (empty)
- `opentofu/gcp/template/.opentofu.lock.hcl` (empty)

**Impact:** No reproducible provider versions across deployments.

**Fix:** Run `tofu init` and commit lock files.

---

### 3. No Root Version Constraint
**Missing from:** Root module (both Azure and GCP templates)

**Impact:** Any OpenTofu version >= 1.0 may be used, risking incompatibilities.

**Fix:** Create `main.tf` with `required_version = ">= 1.5.0, < 2.0"`

---

### 4. Inconsistent Constraints
**DIAL addon:** azurerm `~> 4.0.1` (stricter)
**Main modules:** azurerm `~> 4.0` (looser)

**Impact:** DIAL may fail if main modules use azurerm 4.0.0.

**Fix:** Align all to `~> 4.0`

---

## ✅ What's Actually Defined (Well)

- ✅ Local provider: `~> 2.5` (consistent across 4 modules)
- ✅ Random provider: `~> 3.6` (consistent across 2 modules)
- ✅ Null provider: `~> 3.2` (consistent across 3 modules)
- ✅ Azure provider: `~> 4.0` (mostly consistent, except DIAL addon)

---

## 🎬 Immediate Fix (5 minutes)

### 1. Create Azure Root Module
**File:** `opentofu/azure/template/main.tf`

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0"

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
}
```

### 2. Create GCP Root Module
**File:** `opentofu/gcp/template/main.tf`

Same structure but with `google` instead of `azurerm`.

### 3. Remove `-upgrade` Flag
**Files:**
- `opentofu/azure/template/install.sh` line 23
- `opentofu/gcp/template/install.sh` line 23

```bash
# Change from:
tofu init -upgrade

# Change to:
tofu init
```

### 4. Initialize and Commit Lock Files
```bash
cd opentofu/azure/template
tofu init
git add .opentofu.lock.hcl
git commit -m "Add OpenTofu provider lock file"

cd ../../../opentofu/gcp/template
tofu init
git add .opentofu.lock.hcl
git commit -m "Add OpenTofu provider lock file"
```

---

## 📈 Next Steps (1-2 weeks)

1. **Add constraints to GCP modules** - Explicitly define `google` provider requirements
2. **Add terraform validation** - Create pre-commit hook or GitHub Actions check
3. **Document policy** - Create provider version upgrade policy
4. **Consider Docker** - Use containerized OpenTofu for CI/CD (for production)

---

## 📄 Full Documentation

- **Detailed Report:** `TERRAFORM_VERSION_AUDIT_REPORT.md` (full analysis, 11 sections)
- **JSON Data:** `terraform_audit_report.json` (machine-readable format)
- **This Summary:** `IaC_VERSION_AUDIT_SUMMARY.md` (quick reference)

---

## 🎓 What This Means for Deployment

### Current Situation
```
Developer A deploys on 2026-03-01  → OpenTofu 1.7.2 + azurerm 4.2.1
Developer B deploys on 2026-03-15  → OpenTofu 1.8.0 + azurerm 4.5.0
                                      ↓
                                    Possible incompatibilities
```

### After Fix
```
All deployments use:           → OpenTofu 1.7.2 (pinned in lock file)
All deployments use:           → azurerm 4.2.1 (pinned in lock file)
                                ↓
                              Guaranteed consistency
```

---

## ⏱️ Time Estimate to Fix

| Action | Time | Priority |
|--------|------|----------|
| Create root `main.tf` files | 5 min | 🔴 CRITICAL |
| Remove `-upgrade` flag | 2 min | 🔴 CRITICAL |
| Initialize lock files | 3 min | 🔴 CRITICAL |
| Test deployment | 10 min | 🔴 CRITICAL |
| **Immediate Total** | **20 min** | - |
| Add GCP constraints | 10 min | 🟠 HIGH |
| Add validation checks | 15 min | 🟠 HIGH |
| Document policy | 20 min | 🟡 MEDIUM |
| **Full Implementation** | **~1 hour** | - |

---

## 🤔 FAQ

**Q: Why remove `-upgrade` if it gets the latest versions?**
A: Latest versions can have breaking changes. Lock files ensure reproducible, tested versions. Use `-upgrade` only during intentional upgrades.

**Q: Will this slow down deployments?**
A: No. Lock files are already generated locally; they just reference cached providers.

**Q: What if I need to upgrade providers?**
A: Run `tofu init -upgrade` explicitly when you want to upgrade, test thoroughly, then commit new lock files.

**Q: Are there any GCP-specific issues?**
A: Yes—most GCP modules don't explicitly declare provider requirements. They should be updated to match Azure modules.

**Q: What's the difference between constraints and lock files?**
A: Constraints specify ranges (e.g., `~> 4.0` = 4.0 to 4.99). Lock files pin exact versions (e.g., 4.2.1).

---

**Status:** Audit Complete | Risk: 🔴 HIGH | Fixable: ✅ Yes | Effort: ⏱️ ~20 min immediate
