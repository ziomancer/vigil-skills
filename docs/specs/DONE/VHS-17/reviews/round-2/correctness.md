# Correctness Review — round 2

## Closure of round 1 findings
All round-1 findings CLOSED except edge-cases/F-4 (PARTIAL → resurfaced as F-1 below). Full closure table verified against current spec: correctness F-1/F-2/F-3/F-4, edge-cases F-1/F-2/F-3/F-5/F-6/F-7/F-8, conventions F-1/F-2/F-3/F-4/F-5 all CLOSED.

## Findings

### F-1: D6's factual claim that shipped skills contain "Tools available / fenced reference inventories" naming tools is unsupported (re: edge-cases F-4)
**Severity:** P1
**Where:** spec § D6 (line 45); §4 case 3 (line 101)
Every `mcp__` mention across the four shipped skills carries the full case-2 "(e.g. … or the equivalent in your host)" envelope (spec-cycle:228/237/470; spec-close:378/379; ship-spec:40/219/228/229). There is no bare inventory naming an `mcp__` tool, and grep for "Tools available"/"MCP memory search" returns zero. The case-3 rationale ("would fire on all four shipped skills") is therefore false *as stated* — though bare NON-mcp tool names (Read/Edit/Write/Bash/Agent) do exist in "Tool-use notes" sections (see edge-cases F-1). Re-ground case 3 on the construct that actually exists, or demote it to forward-looking.
**Fix:** Re-ground D6/§4 case 3 on the real "Tool-use notes" bare-tool-name construct, or state case 3 is reserved/forward-looking and cases 1–2 satisfy VHS-18's clean-run criterion.

### F-2: D6 title "permitted only in two of three" contradicts §4 (a harness-specific tool name is permitted in only case 2)
**Severity:** P1
**Where:** spec § D6 title (line 44) vs §4 cases 1–3 (lines 99–101)
Case 1 names a tool (prohibited); case 2 names a tool (allowed); case 3 names the harness-neutral role (allowed, no tool name). So a harness-specific tool *name* appears in exactly one allowed construct, not two. A VHS-18 author reading the title literally would allow `mcp__` tokens in case-3 blocks, which §4 case 3 does not sanction.
**Fix:** Retitle D6 to match §4 precisely (tool names allowed in case 2; case 1 prohibited; case 3 permits only the neutral role / — per F-1 re-grounding — bare tool names in non-operative sections).

## Summary
P0: 0 | P1: 2 | P2: 0 | P3: 0 | P4: 0

STATUS: RED P0=0 P1=2 P2=0 P3=0 P4=0
