# PART 17C — Branching, PR Rules, and Merge Order

**Product (working name):** Rekentafel  
**Repository:** Single monorepo, `main` protected  
**Last updated:** 2026-06-26

---

## 1. Branch model

```
main (protected)
  │
  ├── feature/ws-1/RT-142-guest-claim-sheet
  ├── feature/ws-2/RT-089-staff-bill-entry
  ├── feature/ws-3/RT-031-payment-session-api
  ├── feature/ws-4/RT-012-ui-money-display
  │
  ├── fix/ws-3/RT-201-webhook-idempotency
  └── chore/ws-4/RT-015-turbo-cache-config
```

**No long-lived workstream branches.** All work merges to `main` via PR. Trunk-based with short-lived feature branches (≤3 days preferred).

---

## 2. Branch naming

### 2.1 Format

```
{type}/ws-{n}/{ticket}-{short-kebab-description}
```

| Segment | Required | Values |
|---------|----------|--------|
| `type` | Yes | `feature`, `fix`, `chore`, `docs`, `test` |
| `ws-{n}` | Yes | `ws-1`, `ws-2`, `ws-3`, `ws-4` |
| `ticket` | Yes | Linear/Jira ID, e.g. `RT-142` |
| `short-kebab-description` | Yes | 2–5 words, lowercase |

### 2.2 Examples

| Valid | Invalid | Reason |
|-------|---------|--------|
| `feature/ws-1/RT-142-guest-claim-sheet` | `feature/guest-claim` | Missing ws prefix |
| `fix/ws-3/RT-201-webhook-idempotency` | `ws-3/fix-webhook` | Wrong segment order |
| `feature/ws-2/RT-055-admin-qr-pdf` | `feature/ws-2/ws-1-shared-fix` | Cross-workstream branch name |
| `chore/ws-4/RT-015-ci-contract-diff` | `main-dev` | No personal branches |

### 2.3 Special branches

| Branch | When | Owner |
|--------|------|-------|
| `release/pilot-1` | Pilot cut only; tag after | Platform lead |
| `hotfix/ws-3/RT-999-*` | Production payment bug during pilot | ws-3 + platform lead |

**No `develop` branch.** Staging deploys from `main` HEAD after CI pass.

---

## 3. PR rules

### 3.1 General requirements

| Rule | Enforcement |
|------|-------------|
| Target branch is `main` only | GitHub branch protection |
| 1 approving review from CODEOWNERS path | GitHub |
| CI green (lint, typecheck, test, contract-diff) | GitHub Actions |
| PR title: `[ws-N] RT-xxx: Imperative summary` | Template validation |
| Max 400 lines changed (excluding generated) | Soft — split if reviewer requests |
| Generated files (`guest-hooks/generated`) in separate commit | Convention |

**PR title examples:**

```
[ws-3] RT-031: Add payment session activate endpoint
[ws-1] RT-142: Guest claim sheet with optimistic updates
[ws-4] RT-012: MoneyDisplay primitive and Storybook stories
```

### 3.2 Workstream-specific PR rules

#### ws-3 (contracts / db / api)

| Condition | Extra rule |
|-----------|------------|
| Touches `packages/contracts` | Requires `contract-review` label from ws-1 OR ws-2 reviewer |
| Breaking OpenAPI change | Requires `breaking-change-approved` label (platform lead) |
| Touches `packages/db/prisma/migrations` | Requires migration captain approval comment |
| Touches `apps/api` + `packages/contracts` | Same PR allowed — preferred for atomic API+schema |

#### ws-1 / ws-2 (frontend)

| Condition | Extra rule |
|-----------|------------|
| Depends on unreleased contract | Draft PR until ws-3 contract merges; then rebase |
| Adds ui-core dependency | Link ws-4 Storybook story in PR body |
| Disables MSW for local test | Must not merge to main until integration week flag |

#### ws-4 (infra / ui-core)

| Condition | Extra rule |
|-----------|------------|
| Breaking ui-core change | List affected apps; coordinate merge order guest/staff same day |
| CI workflow change | Notify all ws in Slack before merge |

### 3.3 Forbidden PR patterns

| Pattern | Why blocked |
|---------|-------------|
| PR touches both `apps/guest-web` and `apps/api` | Cross-workstream — split into two PRs |
| PR adds dependency without ws-4 review | Supply chain / bundle size |
| PR merges with failing contract-diff | Breaks parallel consumers |
| PR includes `pnpm-lock.yaml` conflict resolution without rebuild | CI drift |

### 3.4 Draft and stacked PRs

**Stacked PRs allowed within same workstream:**

```
feature/ws-3/RT-030-session-api          (base → main)
  └── feature/ws-3/RT-031-payment-activate (base → RT-030 branch)
```

**Cross-workstream stacks forbidden** — use contract-first sequencing instead.

---

## 4. Merge order contract

When multiple PRs are ready and dependencies exist, merge in this **strict order**:

```
┌─────────────────────────────────────────────────────────────┐
│  TIER 0: ws-4 foundation (config, CI, ui-core tokens)       │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 1: packages/contracts (+ test-fixtures same PR)       │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 2: packages/db migrations (serial, one at a time)     │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 3: apps/api + apps/worker                             │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 4: packages/staff-hooks + apps/staff-web + admin-web  │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 5: packages/guest-hooks + apps/guest-web              │
└─────────────────────────────────────────────────────────────┘
```

**Mnemonic:** **C**ontracts → **A**PI → **S**taff → **G**uest (**C-A-S-G**)

### 4.1 Merge order decision table

| If PR contains… | Merge tier | Blocks |
|-----------------|------------|--------|
| `packages/config`, `turbo.json`, CI only | 0 | Nothing |
| `packages/ui-core` (non-breaking) | 0–1 | Nothing |
| `packages/ui-core` (breaking) | 0, then consumer PRs same day | ws-1, ws-2 |
| `packages/contracts` | 1 | ws-3 api, ws-1, ws-2 hooks |
| `packages/test-fixtures` | 1 (with or immediately after contracts) | ws-1, ws-2 local dev |
| `packages/db/migrations` | 2 | ws-3 api using new columns |
| `apps/api`, `apps/worker` | 3 | Real integration tests |
| `packages/staff-hooks`, staff/admin apps | 4 | Nothing upstream |
| `packages/guest-hooks`, guest app | 5 | Nothing upstream |

### 4.2 Same-day merge batch example

**Scenario:** Add `join_pin_required` boolean to payment session.

| Order | PR | ws | Tier |
|-------|-----|-----|------|
| 1 | `RT-040: Add join_pin_required to PaymentSession schema` | ws-3 | 1 |
| 2 | `RT-041: Enforce PIN on join endpoint` | ws-3 | 3 |
| 3 | `RT-042: Staff toggle for PIN policy` | ws-2 | 4 |
| 4 | `RT-043: Guest PIN entry on join gate` | ws-1 | 5 |

**Do not merge 4 before 1.** ws-1/ws-2 may merge with MSW updated after 1 even before 2 (UI ahead of API is OK with mocks).

### 4.3 Merge queue (GitHub merge queue recommended)

Settings:

- Merge method: **Squash merge**
- Delete branch on merge: **Yes**
- Merge queue: **Enabled** on `main`
- Required checks: `ci/lint`, `ci/typecheck`, `ci/test`, `ci/contract-diff`

**Migration exception:** `packages/db` PRs bypass merge queue — captain merges manually when queue empty.

---

## 5. Rebase vs merge policy

| Situation | Action |
|-----------|--------|
| Feature branch behind `main` | Rebase onto `main` before merge |
| Contract PR merged while frontend PR open | Frontend rebases; regenerate hooks |
| Conflict in `pnpm-lock.yaml` | Rebaser runs `pnpm install` fresh |
| Conflict in generated hooks | Regenerate via `pnpm generate:hooks` |

**No merge commits on feature branches.**

---

## 6. Release and tagging

| Event | Tag format | Branch |
|-------|------------|--------|
| Pilot cut | `pilot-1.0.0` | `release/pilot-1` from `main` |
| Weekly staging snapshot | `staging-YYYY-MM-DD` | `main` HEAD |
| Contract semver | `@rekentafel/contracts@1.x` | npm workspace version in package.json |

**MVP pilot:** Single production deploy from `pilot-1.0.0` tag. Hotfixes branch from tag → PR to `main` → cherry-pick tag `pilot-1.0.1`.

---

## 7. CI gates mapped to merge tiers

```yaml
# Simplified ci.yml job dependency graph
jobs:
  lint-typecheck:     # all PRs
  test-unit:          # affected packages via turbo
  test-contract:      # runs when packages/contracts changes
  contract-diff:      # breaking change detector vs main
  test-e2e-smoke:     # guest menu path — ws-1 + ws-4 paths
  db-migration-check: # prisma validate + drift detect
```

| Job | Blocks merge if fail | Applies to tier |
|-----|---------------------|-----------------|
| `contract-diff` | Yes | 1+ |
| `db-migration-check` | Yes | 2 |
| `test-contract` | Yes | 1, 3 |
| `test-e2e-smoke` | Yes (integration week+) | 5 |

---

## 8. Conflict resolution ownership

| Conflict location | Resolver |
|-------------------|----------|
| `packages/contracts/openapi/*.yaml` | ws-3 author rebases; ws-1/ws-2 never resolve |
| `packages/db/prisma/schema.prisma` | ws-3 migration captain |
| `pnpm-lock.yaml` | PR author runs `pnpm install` |
| `packages/ui-core` + app usage | ws-4 advises; app author rebases |
| `docs/**` | Platform lead |

---

## 9. Emergency procedures (pilot)

### 9.1 Production payment failure

1. ws-3 opens `hotfix/ws-3/RT-xxx-*` from latest pilot tag
2. Platform lead approves bypass of tier 4–5 if API-only fix
3. Deploy API/worker within 2h; frontends unchanged
4. Postmortem in `#rekentafel-incidents`

### 9.2 Contract rollback

If breaking contract merged by mistake:

1. Revert squash commit on `main` (platform lead)
2. ws-3 publishes revert notice in `#contracts-changelog`
3. ws-1/ws-2 revert generated hooks commits

---

## 10. PR template (`.github/pull_request_template.md`)

```markdown
## Workstream
- [ ] ws-1 Guest
- [ ] ws-2 Staff/Admin
- [ ] ws-3 Backend/Payments
- [ ] ws-4 Design/DevOps

## Ticket
RT-___

## Summary
<!-- One paragraph -->

## Merge tier
<!-- 0–5 per branching-and-merge.md -->

## Contract changes
- [ ] No contracts changes
- [ ] Additive only — changelog posted
- [ ] Breaking — `breaking-change-approved` label attached

## NEW_REGISTRY_ENTRIES
<!-- Required if new canonical API/DB names -->

## Test plan
- [ ] Unit tests
- [ ] MSW/fixtures updated
- [ ] Manual steps:

## Screenshots / Loom
<!-- Frontend PRs -->
```

---

## 11. Risks specific to branching strategy

| Risk | Mitigation |
|------|------------|
| Tier inversion (guest merges before contracts) | CI fails on stale generated types; CODEOWNERS block |
| Migration race | Serial merge + captain calendar |
| Squash loses context for audit | PR body + Linear link preserved in commit message |
| Hotfix bypasses review | Platform lead + ws-3 dual approval only |
| Feature flags absent — half-merged API exposed | API routes return 404 until `activate` complete OR use env `FEATURE_*` gates owned by ws-3 |

---

## 12. MVP vs post-MVP branching

| Practice | MVP | V1.1+ |
|----------|-----|-------|
| Merge queue | Optional | Required |
| Release branches | Single `release/pilot-1` | `release/v1.x` per month |
| Feature flags in API | Minimal env gates | LaunchDarkly or similar |
| Contract versioning | v1 only in path | `/v2` parallel branch policy |
| ws ops dashboard | Admin routes in ws-2 | May split ws-5 — not now |
