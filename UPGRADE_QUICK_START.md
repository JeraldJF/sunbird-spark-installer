# Infrastructure Upgrade - Quick Start Guide

**For:** DevOps Engineers & Infrastructure Team
**Time to Read:** 5 minutes
**Time to Execute Phase 1:** 30 minutes

---

## TL;DR

Your infrastructure has **HIGH RISK** of non-reproducible deployments. This needs fixing TODAY.

| Problem | Solution | Time |
|---------|----------|------|
| Uncontrolled OpenTofu version | Add `required_version` blocks | 5 min |
| `-upgrade` flag fetches latest providers | Remove flag from scripts | 5 min |
| Empty lock files | Run `tofu init` | 5 min |
| Uncontrolled K8s versions | Pin to 1.33.6 (AKS) / 1.33.0 (GKE) | 15 min |

**Total for Phase 1:** ~30 minutes | **Risk:** 🟢 LOW | **Impact:** 🔴 CRITICAL

---

## What's Broken?

```
When you deploy today:
├─ OpenTofu version: ??? (whatever's installed on the runner)
├─ Provider versions: Latest (unstable)
├─ K8s version: Auto-selected by cloud provider
└─ Lock files: Empty (no reproducibility)

Result: Same code produces different infrastructure each time! 🚨
```

---

## What We'll Fix

```
After Phase 1:
├─ OpenTofu version: >= 1.8.0, < 2.0 (pinned in code)
├─ Provider versions: Locked in .opentofu.lock.hcl
├─ K8s version: 1.33.6 (pinned in terraform.tfvars)
└─ Every deployment produces identical infrastructure ✅
```

---

## Phase 1: Quick Actions (30 minutes)

### Step 1: Create Azure Root Module (5 min)

Create file: `opentofu/azure/template/main.tf`

```hcl
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

### Step 2: Create GCP Root Module (5 min)

Create file: `opentofu/gcp/template/main.tf`

```hcl
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

### Step 3: Remove `-upgrade` Flags (5 min)

In both files:
- `opentofu/azure/template/install.sh`
- `opentofu/gcp/template/install.sh`

Find:
```bash
tofu init -upgrade
```

Change to:
```bash
tofu init
```

### Step 4: Populate Lock Files (10 min)

```bash
# Azure
cd opentofu/azure/template
tofu init

# GCP
cd opentofu/gcp/template
tofu init
```

Two new files created:
- `opentofu/azure/template/.opentofu.lock.hcl`
- `opentofu/gcp/template/.opentofu.lock.hcl`

### Step 5: Commit Everything (5 min)

```bash
git add opentofu/azure/template/main.tf
git add opentofu/gcp/template/main.tf
git add opentofu/azure/template/.opentofu.lock.hcl
git add opentofu/gcp/template/.opentofu.lock.hcl
# Update install.sh files too
git add opentofu/azure/template/install.sh
git add opentofu/gcp/template/install.sh

git commit -m "Lock OpenTofu and provider versions for reproducibility

- Add required_version blocks to root modules
- Remove -upgrade flag to respect lock files
- Populate .opentofu.lock.hcl for reproducible builds"

git push origin report  # Or your branch
```

---

## Verify Phase 1 Success

```bash
# 1. Check that init works
cd opentofu/azure/template
tofu init
# Should say: "Terraform has been successfully configured!"

# 2. Check that providers are locked
cat .opentofu.lock.hcl | grep version
# Should show specific versions like:
# "version" = "4.32.0"

# 3. Check that -upgrade is gone
grep "\-upgrade" opentofu/*/template/install.sh
# Should return: NO RESULTS
```

---

## Phase 2-5: What's Next?

After Phase 1 is done and committed, you can proceed with:

| Phase | What | When | Duration |
|-------|------|------|----------|
| 1 | Lock versions | **TODAY** | 30 min |
| 2 | Standardize providers | **This week** | 45 min |
| 3 | Pin K8s versions | **This week** | 1 hour |
| 4 | Upgrade clusters | **In 2 weeks** | 4-6 hours |
| 5 | Long-term strategy | **Ongoing** | — |

See `INFRASTRUCTURE_UPGRADE_PLAN.md` for detailed steps for Phases 2-5.

---

## Common Questions

### Q: Will this affect my running clusters?
**A:** No. Phase 1 only adds version constraints. Existing deployments are unchanged.

### Q: What if I don't do this?
**A:** Your next deployment might use different provider versions than today, causing:
- Unexpected infrastructure changes
- Breaking API changes from provider updates
- Non-reproducible bugs
- Data integrity issues

### Q: How do I rollback if something breaks?
**A:**
```bash
git revert <commit-hash>
tofu init  # Uses old versions from before your changes
```

### Q: Can I skip Phase 1?
**A:** No. This is **critical**. It's also the lowest risk, so do it now.

### Q: Do I need to do Phases 2-5 immediately?
**A:** Phase 2-3 should be done this week. Phase 4 (cluster upgrades) can wait 2-4 weeks after Phase 1 is stable.

### Q: What versions am I targeting?

**OpenTofu:** >= 1.8.0, < 2.0 (allows 1.8.x, 1.9.x, but not 2.0)

**Providers:**
- azurerm: ~> 4.0 (allows 4.0-4.63, not 5.0)
- google: ~> 5.0 (allows 5.x)
- tls: ~> 4.0 (allows 4.x)
- local/random/null: Already pinned

**Kubernetes:**
- Current: 1.33.6 (keep for now)
- Next: 1.34.0 (in 2-4 weeks)
- Later: 1.35.x (in 6-8 weeks)

---

## Files Created/Modified

### Created
- ✅ `opentofu/azure/template/main.tf` (new)
- ✅ `opentofu/gcp/template/main.tf` (new)
- ✅ `.opentofu.lock.hcl` (both directories, auto-generated)

### Modified
- ✅ `opentofu/azure/template/install.sh` (remove `-upgrade`)
- ✅ `opentofu/gcp/template/install.sh` (remove `-upgrade`)

---

## Need More Details?

📄 **Full Plan:** [INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md)

📋 **Detailed Checklist:** [UPGRADE_IMPLEMENTATION_CHECKLIST.md](UPGRADE_IMPLEMENTATION_CHECKLIST.md)

📊 **Audit Report:** [AUDIT_FINDINGS.txt](AUDIT_FINDINGS.txt)

🔍 **Current Versions:** [VERSIONS.md](VERSIONS.md)

---

## Support

**Questions?** Check the FAQ in `INFRASTRUCTURE_UPGRADE_PLAN.md` Appendix B.

**Issues?** Open a GitHub issue with:
- What step failed
- Error message
- What you were trying to do

---

## Success Checklist

After Phase 1, you should have:

- [ ] Two new `main.tf` files with `required_version` blocks
- [ ] `-upgrade` flags removed from both `install.sh` scripts
- [ ] Two populated `.opentofu.lock.hcl` lock files
- [ ] All changes committed to git
- [ ] `tofu init` runs without errors
- [ ] `tofu plan` shows no unexpected changes in existing environments

**Once all checkmarks are done:** ✅ Phase 1 Complete!

---

**Ready? Start with Step 1 above. Expected time: 30 minutes.**

