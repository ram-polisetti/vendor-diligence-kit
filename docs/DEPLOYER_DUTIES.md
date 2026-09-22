# Deployer-duties mapping

The kit classifies the vendor's intended use with `ai-act-checker` and maps
each diligence dimension onto the EU AI Act duties that fall on the **deployer**
(the organization buying/adopting the system), not the provider.

## Duty inventory (from the checker's high-risk conformity checklist)

| Article | Duty | What the kit checks |
|---|---|---|
| Art. 26 | Deployer obligations — use per instructions, competent human oversight, monitor operation, report serious incidents | red-team + fairness results feed the monitoring plan; incidents route to the incident runbook |
| Art. 27 | Fundamental rights impact assessment (FRIA) before first use | fairness parity gap and high-risk tier flag the FRIA requirement |
| Art. 43 | Conformity assessment | lineage verification rate shows whether the evidence base exists |
| Art. 49 / Annex VIII | EU database registration | documentation completeness |
| Art. 72 | Post-market monitoring | red-team + fairness batteries are re-runnable; the registry record anchors the baseline |

## How the mapping is built

1. `derive_use_case_tags()` maps the intake's free-text intended use onto the
   checker's tag vocabulary (`recruitment`, `cv_screening`, …) with a
   documented keyword heuristic. **Heuristic, not magic** — the deployer
   should confirm the tags; the report records them.
2. `classify()` returns the risk tier, findings, and conformity checklist.
3. Deployer-facing checklist items are extracted into the battery report.

## Example (demo)

ScreenBot (candidate screening) → tags `recruitment`, `cv_screening`,
`candidate_evaluation` → tier **high-risk** (Annex III, point 4) → 8 deployer
duty items surfaced, including the FRIA requirement and the monitoring duty
that the fairness and red-team results feed into.

## Limits

- Automated triage aid, not legal advice (the checker's own disclaimer).
- The checker's knowledge is dated; verify determinations against the official
  Act text and qualified counsel before placing a system on the market.
- US deployers: the mapping is EU-law-shaped; local obligations still need
  counsel review.
