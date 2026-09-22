"""End-to-end demo: full diligence pipeline against two mock vendors.

Runs intake -> battery -> score -> decide -> report for a weak vendor
(ScreenBot 2.3, planted vulnerabilities) and a remediated one
(ScreenBot 2.4), then prints the comparison and asserts the expected
direction of the results.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "src"))

from diligence import battery as battery_mod
from diligence import intake as intake_mod
from diligence import registry as registry_mod
from diligence import report as report_mod
from diligence import scoring as scoring_mod


def run_vendor(tag: str, answers_file: str, docs_dir: str, target_attr: str,
               approver: str) -> dict:
    out = HERE / "output" / tag
    out.mkdir(parents=True, exist_ok=True)

    raw = json.loads((HERE / answers_file).read_text())
    rec = intake_mod.build_intake(raw, docs_dir=HERE / docs_dir)
    intake_mod.save_intake(rec, out / "intake.json")

    target_ref = f"{HERE / 'mock_vendor.py'}:{target_attr}"
    import importlib.util
    spec = importlib.util.spec_from_file_location("vendor_target",
                                                  HERE / "mock_vendor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    target_fn = getattr(mod, target_attr)

    bat = battery_mod.run_battery(rec, target_fn, target_ref)
    battery_mod.save_battery(bat, out / "battery.json")

    sc = scoring_mod.score(rec, bat)
    (out / "score.json").write_text(json.dumps(sc, indent=2, sort_keys=True))

    dec = registry_mod.write_decision(out / "registry.db", rec, bat, sc,
                                      approver=approver)
    (out / "decision.json").write_text(
        json.dumps(dec, indent=2, sort_keys=True, default=str))

    paths = report_mod.write_report(rec, bat, sc, out / "report", dec)
    return {"tag": tag, "score": sc, "decision": dec, "report": paths}


def main() -> int:
    weak = run_vendor("weak", "answers-weak.json", "docs-weak", "respond",
                      approver="Diligence committee")
    hard = run_vendor("hardened", "answers-hardened.json", "docs-hardened",
                      "respond_hardened", approver="Diligence committee")

    print("\n=== diligence demo: AcmeTalent AI ScreenBot ===")
    for r in (weak, hard):
        sc = r["score"]
        print(f"\n[{r['tag']}] total {sc['total']}/100 -> "
              f"{sc['recommendation'].upper()} (risk {sc['risk_level']}) | "
              f"registry: {r['decision']['registry_decision']}")
        for name, d in sc["dimensions"].items():
            print(f"    {name:20s} {d['score']:6.1f}")

    assert weak["score"]["recommendation"] == "no-go", "weak vendor must be no-go"
    assert weak["decision"]["registry_decision"] == "rejected"
    assert hard["score"]["recommendation"] == "go", \
        f"hardened vendor must be go, got {hard['score']['recommendation']}"
    assert hard["decision"]["registry_decision"] == "approved"
    assert weak["score"]["total"] < hard["score"]["total"]
    print("\ndemo assertions passed: weak -> NO-GO/rejected, "
          "hardened -> GO/approved")
    print(f"reports: {weak['report']['markdown']}")
    print(f"         {hard['report']['markdown']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
