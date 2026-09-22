# Changelog

## 0.1.0 — 2026-09-22

- Initial release.
- `diligence intake`: hashed vendor intake (docs + claims with evidence linkage).
- `diligence run`: test battery — rag-redteam attack suite, opsaudit fairness
  probes, structural lineage checks, ai-act-checker deployer-duties mapping.
- `diligence score`: five-dimension weighted risk score with go/conditional/no-go
  bands and hard blockers (prohibited tier, red-team < 50%).
- `diligence decide`: writes the outcome as the system's first approval record
  in model-governance-registry (go/conditional → approved, no-go → rejected),
  with optional vault sealing (`--seal --pack`).
- `diligence report`: Markdown + JSON diligence report with pinned sibling SHAs.
- Demo: ScreenBot 2.3 (planted weaknesses → 47.1 NO-GO, rejected) vs ScreenBot
  2.4 (remediated → 95.0 GO, approved).
