# Vendor Diligence Kit

A standardized intake for AI models and APIs bought or adopted from outside.
It demands the vendor's documentation, runs a test battery against the system
*as delivered*, checks data-lineage claims, maps findings to EU AI Act
deployer duties, and produces a risk score with a go/no-go recommendation that
is written into the model governance registry as the system's first approval
record.

Procurement gets an evidence-backed decision; governance starts before the
first internal prompt is sent.

## How it works

```
diligence intake  --answers answers.json --docs-dir ./docs   # capture vendor docs + claims (hashed)
diligence run     --intake intake.json --target vendor:ask   # red-team + fairness + lineage + AI Act mapping
diligence score   --intake intake.json --battery battery.json # 5-dimension risk score -> go/conditional/no-go
diligence decide  --registry registry.db --approver "..."    # first approval record in the registry
diligence report  --out ./report                              # human + machine-readable report
```

## Sibling tools (pinned, never reimplemented)

| Tool | Used for | Pinned SHA |
|---|---|---|
| rag-redteam | attack battery (jailbreak, injection, exfiltration, …) | `169e4c8` |
| opsaudit | fairness probes (`audit_disparities`) | `e2f6220` |
| ai-act-checker | EU AI Act tier + deployer duties | `bab26de` |
| model-governance-registry | first approval record | `a8a8a23` |
| governance-evidence-vault | optional bundle sealing (`--seal`) | resolved at runtime |

Set `DILIGENCE_SIBLINGS="rag-redteam=/path,opsaudit=/path,..."` or drop a
`.diligence-siblings.json` in the working directory. Every output records the
pinned SHAs; a checkout mismatch produces a warning, not a silent result.

## Demo

`examples/demo-vendor/` runs the full pipeline against two deterministic mock
vendors: **ScreenBot 2.3** (planted injection, exfiltration, jailbreak and
fairness weaknesses → NO-GO, rejected in the registry) and **ScreenBot 2.4**
(remediated → GO, approved). See `examples/demo-vendor/README.md`.

## Docs

- `docs/METHODOLOGY.md` — what each step does and why
- `docs/SCORING.md` — the scoring model (dimensions, weights, bands, blockers)
- `docs/DEPLOYER_DUTIES.md` — how findings map to EU AI Act deployer duties
- `docs/LIMITATIONS.md` — what this kit cannot do

## License

Apache-2.0
