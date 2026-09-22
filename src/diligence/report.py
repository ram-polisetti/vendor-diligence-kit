"""Human-readable diligence report (Markdown) plus machine JSON."""

from __future__ import annotations

import json
from pathlib import Path


def render_markdown(intake: dict, battery: dict, score: dict,
                    decision: dict | None = None) -> str:
    L = []
    a = L.append
    a(f"# Vendor diligence report: {intake['system_name']}")
    a("")
    a(f"**Vendor:** {intake['vendor_name']}  ")
    a(f"**System version:** {intake.get('system_version', '?')}  ")
    a(f"**Intended use:** {intake['intended_use']}  ")
    a(f"**Deployer context:** {intake['deployer_context']}  ")
    a(f"**Report date:** {battery.get('created_at', '?')}")
    a("")
    a("## Recommendation")
    a("")
    rec = score["recommendation"].upper()
    a(f"**{rec}** — risk score {score['total']}/100 "
      f"(residual risk: {score['risk_level']})")
    a("")
    if score["blockers"]:
        a("**Blocking issues:**")
        for b in score["blockers"]:
            a(f"- {b}")
        a("")
    a("## Dimension scores")
    a("")
    a("| Dimension | Score | Weight | Weighted |")
    a("|---|---|---|---|")
    for name, d in score["dimensions"].items():
        a(f"| {name} | {d['score']} | {d['weight']} | {d['weighted']} |")
    a("")
    for name, d in score["dimensions"].items():
        a(f"### {name} ({d['score']}/100)")
        for n in d["notes"]:
            a(f"- {n}")
        a("")
    a("## Battery details")
    a("")
    rt = battery.get("redteam", {})
    a(f"### Red-team battery (rag-redteam {rt.get('version', '?')})")
    a(f"Overall attack-pass rate: {(rt.get('overall_pass_rate') or 0.0):.1%} "
      f"over {rt.get('n_cases', '?')} cases "
      f"(threshold {rt.get('threshold', 0.8):.0%} — "
      f"{'MET' if rt.get('met_threshold') else 'NOT MET'})")
    for fam in rt.get("families", []):
        a(f"- {fam.get('family')}: {(fam.get('pass_rate') or 0.0):.1%} "
          f"({fam.get('passed')}/{fam.get('total')})")
    a("")
    fair = battery.get("fairness", {})
    a("### Fairness probes (opsaudit)")
    a(f"Max demographic-parity gap: "
      f"{fair.get('max_demographic_parity_diff')}")
    a(f"Unparseable responses: {fair.get('unparseable_responses')}")
    a(f"_{fair.get('note', '')}_")
    a("")
    lin = battery.get("lineage", {})
    a("### Lineage checks")
    a(f"Verified claims: {lin.get('n_verified')}/{lin.get('n_claims')} "
      f"({(lin.get('verification_rate') or 0.0):.0%})")
    for c in lin.get("claims", []):
        a(f"- [{c.get('status')}] {c.get('text', '')[:120]}")
    a("")
    dd = battery.get("deployer_duties", {})
    a("### EU AI Act deployer duties (ai-act-checker)")
    a(f"Tier: **{dd.get('tier', '?')}**")
    for duty in dd.get("deployer_duties", []):
        a(f"- **{duty.get('article')} — {duty.get('item')}:** {duty.get('detail')}")
    a("")
    if decision:
        a("## Registry record")
        a("")
        a(f"System registered as `{decision['system']}`; first approval record: "
          f"**{decision['registry_decision']}** "
          f"(diligence recommendation: {decision['diligence_recommendation']}).")
        a(f"Registry: `{decision['registry_path']}`")
        a("")
    pins = battery.get("sibling_pins", {})
    if pins:
        a("## Reproducibility")
        a("")
        for name, sha in pins.items():
            a(f"- {name}: `{sha}`")
    warns = battery.get("sibling_warnings", [])
    for w in warns:
        a(f"> ⚠ {w}")
    a("")
    return "\n".join(L)


def write_report(intake: dict, battery: dict, score: dict,
                 out_dir: str | Path, decision: dict | None = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md = render_markdown(intake, battery, score, decision)
    md_path = out_dir / "diligence-report.md"
    md_path.write_text(md)
    bundle = {"intake": intake, "battery": battery, "score": score,
              "decision": decision}
    json_path = out_dir / "diligence-report.json"
    json_path.write_text(json.dumps(bundle, indent=2, sort_keys=True, default=str))
    return {"markdown": str(md_path), "json": str(json_path)}
