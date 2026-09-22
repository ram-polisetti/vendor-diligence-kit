"""Registry adapter: write the diligence outcome as the first approval record.

Mapping (documented in docs/METHODOLOGY.md):
- recommendation "go"          -> registry decision "approved"
- recommendation "conditional" -> registry decision "approved", with the
  conditions spelled out in the rationale and linked evidence
- recommendation "no-go"       -> registry decision "rejected"

The registry only allows approved/rejected, so a conditional outcome is a
qualified approval, never a silent third state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import siblings


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_card(intake: dict, battery: dict) -> dict:
    docs = intake.get("doc_kinds_present", [])
    rt = battery.get("redteam", {})
    fair = battery.get("fairness", {})
    return {
        "purpose": (f"Third-party AI system under vendor diligence: "
                    f"{intake['system_name']} v{intake.get('system_version', '?')} "
                    f"from {intake['vendor_name']}."),
        "intended_use": intake["intended_use"],
        "training_data": ("Vendor claims: "
                          + "; ".join(c["text"] for c in intake.get("claims", [])
                                       if c.get("category") == "training_data_claims")
                          or "no training-data claims captured"),
        "evaluation": (f"Red-team battery overall pass rate "
                       f"{(rt.get('overall_pass_rate') or 0.0):.1%}; max fairness "
                       f"parity gap {(fair.get('max_demographic_parity_diff') or 0.0):.3f}. "
                       f"Vendor documents on file: {', '.join(docs) or 'none'}."),
        "limitations": ("Card assembled from vendor-supplied intake plus "
                        "independent battery runs by the diligence kit; vendor "
                        "claims are structurally verified (doc linkage), not "
                        "independently audited."),
    }


def _build_risk(score: dict, battery: dict) -> tuple[dict, str]:
    dims = score["dimensions"]
    overall = score["risk_level"]
    content = {
        "govern": ("Diligence performed by the vendor-diligence-kit; recommendation "
                   f"{score['recommendation']} (total {score['total']}/100). "
                   "Human decision required before procurement."),
        "map": ("Use case classified under the EU AI Act as "
                f"{battery.get('deployer_duties', {}).get('tier', 'unknown')}; "
                f"{len(battery.get('deployer_duties', {}).get('deployer_duties', []))} "
                "deployer duty item(s) identified."),
        "measure": ("; ".join(f"{name} {d['score']}/100 (w {d['weight']})"
                              for name, d in dims.items())),
        "manage": ("Blockers: " + ("; ".join(score["blockers"]) if score["blockers"]
                                   else "none") + ". Residual risk owned by the "
                   "deployer under Art. 26 monitoring duties."),
    }
    return content, overall


def write_decision(registry_path: str | Path, intake: dict, battery: dict,
                   score: dict, approver: str, actor: str = "diligence-kit"
                   ) -> dict:
    """Write the full diligence outcome into the registry; return the record."""
    siblings.import_sibling("model-governance-registry")
    from mgreg.store import Registry

    store = Registry(str(registry_path))
    sys_name = f"{intake['vendor_name']} — {intake['system_name']}"
    try:
        model = store.register(sys_name, owner=intake["vendor_name"], actor=actor)
    except Exception:  # already registered; reuse
        model = store.get_model(sys_name)
    model_id = model["id"]

    if store.get_model(model_id)["status"] != "under_review":
        try:
            store.set_status(model_id, "under_review", actor)
        except Exception:
            pass  # e.g. already under_review

    card = store.add_card(model_id, _build_card(intake, battery),
                          created_by=actor, actor=actor)
    risk_content, overall_risk = _build_risk(score, battery)
    risk = store.add_risk(model_id, risk_content, overall_risk=overall_risk,
                          created_by=actor, actor=actor)

    evidence_ids = []
    for kind, summary, payload in (
        ("document", {"title": "vendor intake record"},
         {"intake": intake}),
        ("document", {"title": "diligence battery report"},
         {"battery": battery}),
        ("document", {"title": "diligence scoring report"},
         {"score": score}),
    ):
        ev = store.attach_evidence(model_id, kind, summary, payload,
                                   created_by=actor, actor=actor)
        evidence_ids.append(ev["id"])

    rec = score["recommendation"]
    decision = "rejected" if rec == "no-go" else "approved"
    rationale = (
        f"Vendor diligence recommendation: {rec} "
        f"(risk score {score['total']}/100, residual risk {overall_risk}). "
    )
    if rec == "conditional":
        conds = []
        for name, dim in score["dimensions"].items():
            if dim["score"] < 75:
                conds.append(f"{name} scored {dim['score']}/100: "
                             + "; ".join(dim["notes"][:2]))
        rationale += "CONDITIONS FOR PROCUREMENT: " + " | ".join(conds)
    elif rec == "go":
        rationale += "No blocking issues; standard Art. 26 deployer monitoring applies."
    else:
        rationale += "BLOCKERS: " + "; ".join(score["blockers"] or
                                              ["score below no-go threshold"])

    approval = store.record_approval(model_id, approver=approver,
                                     decision=decision, rationale=rationale,
                                     evidence_ids=evidence_ids, actor=actor)
    return {
        "model_id": model_id,
        "system": sys_name,
        "card_version": card["version"],
        "risk_version": risk["version"],
        "evidence_ids": evidence_ids,
        "registry_decision": decision,
        "diligence_recommendation": rec,
        "approval": approval,
        "registry_path": str(registry_path),
    }
