# Edge-Cases Review — round 3

## Closure of round 2 findings
All seven round-2 findings (correctness F-1/F-2, edge-cases F-1–F-5) verified CLOSED against current spec text and the four shipped SKILL.md files.

## Findings

### F-1: Broadened case 3 ("regardless of phrasing") opens a by-heading false-negative hole
**Severity:** P2 — **Pre-ship recommended: yes**
**Where:** spec §4 case 3 (line 105) vs §4 closing paragraph (line 107); D6 (line 49)
A future author could write an operative imperative containing a bare tool call ("First call `mcp__plane__retrieve_work_item` to fetch the ticket, then…") and place it under a "Tool-use notes" heading. A VHS-18 lint built literally to §4 — which exempts notes sections "regardless of phrasing" and identifies them by heading/type, not content — silently passes it, defeating the case-1 prohibition that is VHS-18's whole reason to exist. Latent (no shipped skill exploits it today), so the lint runs clean now; the hole is triggered only by a future authoring pattern. Lines 105 and 107 are in tension (105: notes-section tool names case 3 regardless of phrasing; 107: executed step is case 1).
**Fix:** Scope the case-3 exemption to *non-operative content* even within a notes section: an operative imperative is case 1 regardless of heading; a notes/reference heading raises a presumption of non-operativeness, it does not override an operative imperative. Resolves the 105↔107 tension and keeps case 1 sound.

## Summary
P0: 0 | P1: 0 | P2: 1 | P3: 0 | P4: 0

Notes (no findings): operativeness is statically decidable (heading allowlist + fenced-block detection — correct altitude, VHS-18 enforces); no remaining load-bearing tokenization corner (inline `requires: []`/`{}` harmless — zero indented lines → none; nested mapping → violation per line 96). Spec is implementable as written; F-1 is soundness-hardening, not a blocker.

STATUS: RED P0=0 P1=0 P2=1
