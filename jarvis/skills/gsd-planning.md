# GSD Planning (Get Shit Done)

Apply spec-driven development patterns from GSD when decomposing or executing builds:

## Decomposition principles

1. **Phase pipeline**: discuss → plan → execute → verify
2. Each slice is a **phase** with clear entry/exit criteria
3. Assign **disjoint file ownership** — no two slices edit the same file
4. Lock the **tech stack** in slice 1; downstream slices inherit it
5. Foundations before features; integrations last
6. Every slice ends with a **verifiable artifact** (not just code written)

## Variable registry (GSD-style)

- Canonical names are decided at PRD time, not invented per slice
- New names require `NEW_REGISTRY_ENTRIES` block at slice completion
- Cross-slice contracts reference registry names exactly

## Namespace routing (when user asks for GSD commands)

| Intent | Approach |
|--------|----------|
| Project setup | Scaffold + PRD + registry in first 2 slices |
| Phase plan | Decompose into 8–20 slices with deps |
| Quality gate | Add validation slice before integration |
| Ship | Final integration + test slice |

## External install

For full GSD in Cursor/Claude: `npx get-shit-done-cc --cursor --global`

Jarvis uses these patterns natively in the build pipeline — no separate GSD runtime required.
