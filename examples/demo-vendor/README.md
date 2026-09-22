# Demo: AcmeTalent AI ScreenBot

Runs the full diligence pipeline against two deterministic mock vendors
(`mock_vendor.py`) — no network, no randomness, repeatable.

- **ScreenBot 2.3** (`respond`) — planted weaknesses: follows injected
  instructions, echoes attacker canaries, leaks hidden context, gives
  ungrounded answers, screens candidates unfairly.
- **ScreenBot 2.4** (`respond_hardened`) — remediated: refuses injections,
  never leaks, abstains cleanly, screens fairly.

```bash
export DILIGENCE_SIBLINGS="rag-redteam=/path/to/rag-redteam,opsaudit=/path/to/opsaudit,ai-act-checker=/path/to/ai-act-checker,model-governance-registry=/path/to/model-governance-registry"
PYTHONPATH=../../src python3 demo.py
```

Expected: 2.3 → **47.1 NO-GO** (rejected in the registry); 2.4 → **95.0 GO**
(approved). The demo asserts this direction and fails otherwise.

`answers-*.json` are the intake questionnaires; `docs-weak/` and
`docs-hardened/` are the vendor document packs (the weak vendor is missing its
data statement and evaluation summary, and two of its claims name no
evidence).
