# Infrastructure Upgrade Analysis - Executive Summary

**Analysis Date:** 2026-03-16
**Risk Level:** 🔴 **CRITICAL**
**Recommendation:** Proceed with Phase 1 immediately (today)

---

## Problem Statement

Your Sunbird Spark infrastructure uses OpenTofu/Terraform with **ZERO version control**, creating non-reproducible deployments:

```
Same code → Different infrastructure (each deployment)
```

This is caused by four critical gaps:

| Gap | Impact | Severity |
|-----|--------|----------|
| No OpenTofu version pinning | System default (1.0+) used | 🔴 Critical |
| `-upgrade` flag in scripts | Latest provider versions fetched every time | 🔴 Critical |
| Empty lock files | Provider versions not reproducible | 🔴 Critical |
| No K8s version constraints | Uncontrolled cluster versions | 🔴 Critical |

---

## Why This Matters

### Scenario 1: Production Bug
```
Dev cluster: Uses provider 4.0.0
Prod cluster: Uses provider 4.32.0 (latest)
Result: Same code, different behavior
         → Bug in prod doesn't reproduce in dev
         → Can't debug, can't fix
```

### Scenario 2: Surprise Breaking Changes
```
Deploy on Monday: Works (uses provider 4.20.0)
Deploy on Wednesday: Fails (provider 4.30.0 has breaking changes)
What changed in code? Nothing!
What changed in provider? Breaking API
```

### Scenario 3: Kubernetes Version Mismatch
```
AKS cluster: 1.33.6 (what's installed now)
Next deployment: 1.35.0 (Azure latest)
Result: Unknown compatibility issues
         Cluster recreated unexpectedly
         Potential data loss if not handled right
```

---

## Current State vs Target State

### Current State (BROKEN)
```hcl
# opentofu/azure/template/install.sh
tofu init -upgrade  # ← Fetches LATEST provider versions
tofu apply

# Result: Latest provider versions used
# Problem: Different run = different versions!

# .opentofu.lock.hcl
# (empty or not committed)

# Kubernetes version: Auto-selected by cloud provider
# (uncontrolled, can change)
```

### Target State (FIXED)
```hcl
# opentofu/azure/template/main.tf
terraform {
  required_version = ">= 1.8.0, < 2.0"
  required_providers {
    azurerm = {
      version = "~> 4.0"  # ← Specific range
    }
  }
}

# opentofu/azure/template/install.sh
tofu init  # ← Uses lock file (no -upgrade)
tofu apply

# Result: Same provider versions every time
# Benefit: Reproducible deployments!

# .opentofu.lock.hcl
# Contains exact versions: azurerm = 4.32.0 (locked)

# Kubernetes version: 1.33.6 (pinned in terraform)
# (controlled, known)
```

---

## Solution Overview

### Phase 1: Emergency Fix (TODAY) 🚨
**Time:** 30 minutes | **Risk:** 🟢 LOW | **Impact:** 🔴 CRITICAL

Add version constraints to code, remove `-upgrade` flag, lock providers.

✅ SAFE ON EXISTING CLUSTERS (no changes to running infrastructure)

### Phase 2: Consistency (THIS WEEK)
**Time:** 45 minutes | **Risk:** 🟡 LOW | **Impact:** 🟢 MEDIUM

Standardize provider versions across all modules.

✅ SAFE ON EXISTING CLUSTERS (audit + standardize only)

### Phase 3: K8s Pinning (THIS WEEK)
**Time:** 1 hour | **Risk:** 🟡 MEDIUM | **Impact:** 🟢 HIGH

Pin Kubernetes versions to current stable releases.

✅ SAFE ON EXISTING CLUSTERS (pins current versions only)

### Phase 4: Cluster Upgrades (IN 2 WEEKS)
**Time:** 4-6 hours per cluster | **Risk:** 🟠 MEDIUM | **Impact:** 🟢 HIGH

Roll clusters from 1.33.6 → 1.34.0 (minor version, backward compatible).

⚠️ REQUIRES ROLLING UPGRADE (transient downtime during node updates)

### Phase 5: Long-Term (ONGOING)
**Time:** Quarterly reviews | **Risk:** 🟡 MEDIUM | **Impact:** 🟢 MEDIUM

Plan future upgrades (1.35.0, provider 5.0, etc.) systematically.

---

## Version Targets

### Current vs Target

| Component | Current | Phase 1 | Phase 3 | Phase 4 | Phase 5 |
|-----------|---------|---------|---------|---------|---------|
| **OpenTofu Binary** | Uncontrolled | >= 1.8.0, < 2.0 | >= 1.8.0, < 2.0 | >= 1.8.0, < 2.0 | >= 1.8.0, < 2.0 |
| **azurerm Provider** | ~> 4.0 (implicit max) | ~> 4.0 | ~> 4.0 | ~> 4.0 | ~> 5.0 (later) |
| **google Provider** | Implicit (no constraint) | ~> 5.0 | ~> 5.0 | ~> 5.0 | ~> 5.0 |
| **tls Provider** | None | ~> 4.0 | ~> 4.0 | ~> 4.0 | ~> 4.0 |
| **AKS K8s** | 1.33.6 (auto) | 1.33.6 (pinned) | 1.33.6 (pinned) | 1.34.0 | 1.35.x |
| **GKE K8s** | Unknown | Unknown | 1.33.0 (pinned) | 1.34.0 | 1.35.x |

### Why These Versions?

- **OpenTofu 1.8.0:** Stable, not cutting edge, safe for production
- **azurerm 4.0:** Current stable line, 0.63 versions behind latest (acceptable)
- **google 5.0:** Current stable line
- **tls 4.0:** Current stable line
- **K8s 1.33.6:** Current production version (proven stable)
- **K8s 1.34.0:** Next minor version (2-4 weeks out for safety)
- **K8s 1.35.x:** Latest (wait for broader adoption)

---

## What Gets Fixed in Each Phase

### Phase 1 Fixes
```
BEFORE:
❌ No OpenTofu version constraint
   → Every run uses whatever is installed
❌ -upgrade flag in scripts
   → Always downloads latest providers
❌ Lock files empty
   → Provider versions differ between runs
❌ No K8s version in code
   → Cloud provider auto-selects

AFTER Phase 1:
✅ OpenTofu >= 1.8.0, < 2.0 in terraform block
✅ -upgrade flag removed
✅ Lock files populated and locked to specific versions
✅ K8s version pinned to current stable (1.33.6)
✅ Next deployment produces identical infrastructure
```

### Phase 2 Fixes
```
BEFORE:
❌ 5 GCP modules have no provider constraints
❌ 2 modules have implicit TLS provider
❌ DIAL addon uses stricter constraint (4.0.1 vs 4.0)

AFTER Phase 2:
✅ All 16 modules have explicit provider constraints
✅ TLS provider pinned to 4.0
✅ DIAL addon aligned with main modules
✅ Consistent policy across all modules
```

### Phase 3 Fixes
```
BEFORE:
❌ AKS K8s version auto-selected by Azure
❌ GKE K8s version uncontrolled
❌ No K8s version policy

AFTER Phase 3:
✅ AKS pinned to 1.33.6 in terraform code
✅ GKE pinned to 1.33.0 in terraform code
✅ Version policy documented
✅ Explicit control over when K8s upgrades happen
```

### Phase 4 Fixes
```
BEFORE:
❌ Running on 1.33.6
❌ Can't control when K8s upgrades
❌ Possible compatibility issues with new versions

AFTER Phase 4:
✅ All clusters on 1.34.0
✅ Validated safe (tested on dev → staging → prod)
✅ Known version compatibility
✅ Ready for 1.35 upgrade planning
```

---

## Risk Matrix

### Phase 1: Adding Version Constraints
| Aspect | Status | Details |
|--------|--------|---------|
| **Breaks existing code?** | ✅ NO | Only adds constraints, no logic changes |
| **Requires cluster restart?** | ✅ NO | No changes to running infrastructure |
| **Data loss risk?** | ✅ NO | No infrastructure changes |
| **Rollback difficulty?** | ✅ EASY | `git revert` and `tofu init` |
| **Can be automated?** | ✅ YES | Simple file edits and commands |

**Verdict:** 🟢 **SAFE, DO TODAY**

### Phase 2: Provider Standardization
| Aspect | Status | Details |
|--------|--------|---------|
| **Breaks existing code?** | ✅ NO | Standardizes, doesn't change |
| **Requires cluster restart?** | ✅ NO | Audit-only phase |
| **Data loss risk?** | ✅ NO | No infrastructure changes |
| **Rollback difficulty?** | ✅ EASY | Revert constraint changes |
| **Testing required?** | ⚠️ YES | Run `tofu validate` on all modules |

**Verdict:** 🟡 **SAFE, DO THIS WEEK**

### Phase 3: K8s Version Pinning
| Aspect | Status | Details |
|--------|--------|---------|
| **Breaks existing code?** | ✅ NO | Pins current versions only |
| **Requires cluster restart?** | ✅ NO | No changes to infrastructure |
| **Data loss risk?** | ✅ NO | No infrastructure changes |
| **Rollback difficulty?** | ✅ EASY | Revert constraint variable |
| **Testing required?** | ⚠️ YES | Dry-run `tofu plan` on each environment |

**Verdict:** 🟡 **SAFE, DO THIS WEEK**

### Phase 4: K8s Cluster Upgrades
| Aspect | Status | Details |
|--------|--------|---------|
| **Breaks existing code?** | ✅ NO | Upgrade is seamless |
| **Requires cluster restart?** | 🟠 YES | Rolling upgrade (no downtime) |
| **Data loss risk?** | ✅ NO | Velero backup before upgrade |
| **Rollback difficulty?** | 🟠 HARD | Requires re-downgrade |
| **Testing required?** | 🔴 YES | Test on dev first, then staging |

**Verdict:** 🟠 **MEDIUM RISK, WAIT 2+ WEEKS**

---

## Why Wait 2 Weeks for Phase 4?

Phase 1-3 establish version control. Phase 4 actually upgrades.

**Why the wait?**
1. Verify Phase 1-3 are stable in production (1-2 weeks of normal traffic)
2. Ensure lock files are working as expected
3. Validate that pinned versions don't cause issues
4. Have runbooks and procedures ready
5. Let team familiarize with new process

**If you skip the wait:**
- Higher risk of rolling back if issues found
- Less confidence in version control system
- Harder to debug problems post-upgrade

---

## Breaking Changes to Watch For

### None Expected in Phase 1-3
These phases are purely additive (add constraints, no changes to running infrastructure).

### Phase 4: K8s 1.33 → 1.34
**Risk Level:** 🟢 LOW (minor version, backward compatible)

**Potential Issues:**
- Deprecated APIs in 1.34 (unlikely to affect Sunbird)
- Changes in kubelet behavior (Azure handles automatically)
- Changes in RBAC or network policy (unlikely)

**Mitigation:** Test on dev first, validate all workloads

### Phase 5: K8s 1.35+
**Risk Level:** 🟡 MEDIUM (depends on app code)

**Potential Issues:** TBD (will assess when 1.35 released)

---

## Parallel Work Opportunities

**Phase 1 tasks (all parallelizable):**
- Create Azure main.tf
- Create GCP main.tf
- Update Azure install.sh
- Update GCP install.sh
- Run tofu init (after main.tf created)
- Update DIAL addon

**Estimated Time with 1 person:** 30 minutes (sequential)
**Estimated Time with 2 people:** 20 minutes (parallel)

**Phase 2 tasks (mostly parallelizable):**
- Update 7 GCP modules (independent)
- Audit 6 Azure modules (independent)
- Can do in parallel

**Estimated Time:** 45 minutes for 1-2 people

---

## What We Created for You

### 4 Implementation Documents

1. **[INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md)** (20 KB)
   - Complete 5-phase plan with technical details
   - All file paths, code snippets, rationales
   - Timeline and success criteria
   - Risk assessment and rollback procedures

2. **[UPGRADE_QUICK_START.md](UPGRADE_QUICK_START.md)** (5 KB)
   - Fast-track for Phase 1 (30 minutes)
   - Copy-paste code for main.tf files
   - Step-by-step verification
   - Common questions answered

3. **[UPGRADE_IMPLEMENTATION_CHECKLIST.md](UPGRADE_IMPLEMENTATION_CHECKLIST.md)** (10 KB)
   - Checkbox form for each task
   - Sign-off sections
   - Issue tracker
   - Team accountability

4. **[UPGRADE_ANALYSIS_SUMMARY.md](UPGRADE_ANALYSIS_SUMMARY.md)** (this document)
   - Executive overview
   - Risk analysis
   - Why it matters
   - Timeline summary

---

## Recommended Next Steps

### TODAY
1. **Read:** [UPGRADE_QUICK_START.md](UPGRADE_QUICK_START.md) (5 minutes)
2. **Execute:** Phase 1 steps (30 minutes)
3. **Commit:** Push changes to git
4. **Verify:** Run `tofu init && tofu plan` checks

### THIS WEEK
1. **Review:** [INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md) Phases 2-3
2. **Execute:** Phase 2 (45 minutes)
3. **Execute:** Phase 3 (1 hour)
4. **Test:** Dry-run `tofu plan` on dev environment

### NEXT WEEK
1. **Monitor:** Phase 1-3 changes in production
2. **Plan:** Phase 4 cluster upgrade schedule
3. **Document:** Team runbooks
4. **Train:** Team on new version process

### IN 2 WEEKS
1. **Execute:** Phase 4 dev cluster upgrade
2. **Validate:** Stability and workload compatibility
3. **Execute:** Phase 4 staging upgrade
4. **Execute:** Phase 4 production upgrade
5. **Document:** Lessons learned

---

## Success Metrics

After completing this plan, you'll have:

✅ **Reproducibility:** Same code = same infrastructure (every time)
✅ **Predictability:** Know exactly which versions will be deployed
✅ **Safety:** Can test upgrades on dev before production
✅ **Control:** Consciously choose when to upgrade (not automatic)
✅ **Auditability:** Version decisions documented in git
✅ **Rollback:** Easy to revert to previous versions if needed

---

## Questions?

| Question | Answer | Resource |
|----------|--------|----------|
| What is the full plan? | 5 phases over 8 weeks | [INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md) |
| How do I get started today? | Phase 1 in 30 minutes | [UPGRADE_QUICK_START.md](UPGRADE_QUICK_START.md) |
| What file do I edit first? | opentofu/azure/template/main.tf | [UPGRADE_QUICK_START.md](UPGRADE_QUICK_START.md) Step 1 |
| Can I automate this? | Phase 1-3 yes, Phase 4 needs approval | [INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md) |
| What if it breaks? | Easy rollback with git revert | [INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md) Rollback section |
| How long does Phase 1 take? | 30 minutes | [UPGRADE_QUICK_START.md](UPGRADE_QUICK_START.md) |
| Do I need downtime? | No for Phases 1-3, rolling upgrade for Phase 4 | [INFRASTRUCTURE_UPGRADE_PLAN.md](INFRASTRUCTURE_UPGRADE_PLAN.md) |

---

## Bottom Line

| What | Status | Action | Timeline |
|------|--------|--------|----------|
| **Risk Level** | 🔴 CRITICAL | Proceed immediately | TODAY |
| **Phase 1** | 🟢 READY | Execute today | 30 min |
| **Phases 2-3** | 🟡 PLANNED | Execute this week | 2 hours |
| **Phase 4** | ⏳ SCHEDULED | Execute in 2-4 weeks | 6 hours |
| **Phase 5** | 📅 ONGOING | Quarterly reviews | Ongoing |

**Your infrastructure needs version control. Start with Phase 1 today.**

---

**Last Updated:** 2026-03-16
**Prepared by:** DevOps Architecture Team
**For:** Sunbird Spark Infrastructure

