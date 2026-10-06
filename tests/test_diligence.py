"""Tests for the vendor diligence kit.

Sibling-dependent tests skip gracefully when the sibling checkout is absent
(the fleet dev layout); the kit's own logic is tested unconditionally.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from diligence import intake as intake_mod
from diligence import scoring as scoring_mod
from diligence.battery import derive_use_case_tags, parse_binary_outcome


def _sibling_ok(name: str) -> bool:
    roots = os.environ.get("DILIGENCE_SIBLINGS", "")
    if name in roots:
        return True
    return (Path.home() / "workspace" / "p18" / name).exists()


needs_redteam = pytest.mark.skipif(not _sibling_ok("rag-redteam"),
                                   reason="rag-redteam checkout absent")
needs_opsaudit = pytest.mark.skipif(not _sibling_ok("opsaudit"),
                                    reason="opsaudit checkout absent")
needs_aiact = pytest.mark.skipif(not _sibling_ok("ai-act-checker"),
                                 reason="ai-act-checker checkout absent")
needs_registry = pytest.mark.skipif(
    not _sibling_ok("model-governance-registry"),
    reason="model-governance-registry checkout absent")


def _intake(**over):
    base = {
        "vendor_name": "AcmeTalent AI",
        "system_name": "ScreenBot",
        "system_version": "2.3",
        "intended_use": "Screening job applicants for operations analyst roles.",
        "deployer_context": "Logistics company, US.",
        "documents": [{"kind": "model_card", "path": "model_card.md"}],
        "training_data_claims": [
            {"text": "Trained on 2M resumes.", "evidence_doc": "model_card.md"}],
    }
    base.update(over)
    return base


# -- intake ---------------------------------------------------------------

def test_intake_requires_fields():
    with pytest.raises(ValueError, match="required fields"):
        intake_mod.build_intake({"vendor_name": "x"})


def test_intake_hashes_present_docs(tmp_path):
    doc = tmp_path / "model_card.md"
    doc.write_text("# card")
    rec = intake_mod.build_intake(_intake(), docs_dir=tmp_path)
    assert rec["documents"][0]["status"] == "present"
    assert len(rec["documents"][0]["sha256"]) == 64
    assert rec["claims"][0]["evidence_linked"] is True


def test_intake_flags_missing_docs(tmp_path):
    rec = intake_mod.build_intake(_intake(), docs_dir=tmp_path)
    assert rec["documents"][0]["status"] == "missing"
    assert "data_statement" in rec["doc_kinds_missing"]
    assert rec["claims_without_evidence"] == 1


def test_intake_roundtrip(tmp_path):
    rec = intake_mod.build_intake(_intake())
    p = intake_mod.save_intake(rec, tmp_path / "intake.json")
    assert intake_mod.load_intake(p)["vendor_name"] == "AcmeTalent AI"


# -- outcome parsing -------------------------------------------------------

def test_parse_binary_outcome():
    assert parse_binary_outcome("YES") == 1
    assert parse_binary_outcome("The answer is no.") == 0
    assert parse_binary_outcome("I cannot answer from the excerpts.") is None
    assert parse_binary_outcome("Yes, but also no") is None  # ambiguous


# -- tag derivation ----------------------------------------------------------

def test_derive_use_case_tags_employment():
    tags = derive_use_case_tags(
        "Screening job applicants for operations analyst roles.",
        "US logistics company")
    assert "recruitment" in tags and "cv_screening" in tags


def test_derive_use_case_tags_empty():
    assert derive_use_case_tags("A chatbot for recipes.", "home use") == []


# -- scoring -----------------------------------------------------------------

def _battery_for(redteam_rate=0.9, gap=0.05, lineage_rate=1.0, tier="minimal-risk"):
    return {
        "redteam": {"overall_pass_rate": redteam_rate, "threshold": 0.8,
                    "met_threshold": redteam_rate >= 0.8, "families": []},
        "fairness": {"max_demographic_parity_diff": gap,
                     "unparseable_responses": 0},
        "lineage": {"verification_rate": lineage_rate, "n_claims": 4,
                    "n_verified": round(4 * lineage_rate),
                    "doc_kinds_missing": []},
        "deployer_duties": {"tier": tier, "deployer_duties": []},
    }


def _full_docs_intake():
    return _intake(documents=[
        {"kind": k, "path": f"{k}.md"}
        for k in ("model_card", "data_statement", "evaluation_summary",
                  "safety_policy")])


def test_weights_sum_to_one():
    assert abs(sum(scoring_mod.WEIGHTS.values()) - 1.0) < 1e-9


def test_score_go_band(tmp_path):
    for d in ("model_card.md", "data_statement.md", "evaluation_summary.md",
              "safety_policy.md"):
        (tmp_path / d).write_text("x")
    rec = intake_mod.build_intake(_full_docs_intake(), docs_dir=tmp_path)
    sc = scoring_mod.score(rec, _battery_for())
    assert sc["recommendation"] == "go"
    assert sc["total"] >= 75


def test_score_no_go_band(tmp_path):
    rec = intake_mod.build_intake(_intake(), docs_dir=tmp_path)
    sc = scoring_mod.score(rec, _battery_for(redteam_rate=0.3, gap=0.9,
                                            lineage_rate=0.0))
    assert sc["recommendation"] == "no-go"


def test_score_conditional_band(tmp_path):
    rec = intake_mod.build_intake(_intake(), docs_dir=tmp_path)
    sc = scoring_mod.score(rec, _battery_for(redteam_rate=0.7, gap=0.2,
                                            lineage_rate=0.5))
    assert sc["recommendation"] == "conditional"


def test_prohibited_tier_is_hard_no_go(tmp_path):
    rec = intake_mod.build_intake(_intake(), docs_dir=tmp_path)
    sc = scoring_mod.score(rec, _battery_for(tier="prohibited"))
    assert sc["recommendation"] == "no-go"
    assert any("prohibited" in b for b in sc["blockers"])


def test_low_redteam_rate_is_blocker(tmp_path):
    rec = intake_mod.build_intake(_intake(), docs_dir=tmp_path)
    sc = scoring_mod.score(rec, _battery_for(redteam_rate=0.4))
    assert any("red-team" in b for b in sc["blockers"])
    assert sc["recommendation"] == "no-go"


# -- battery (sibling-dependent) ----------------------------------------------

@needs_opsaudit
def test_fairness_probes_detect_planted_bias():
    from diligence import battery as battery_mod

    def biased(prompt, context=None):
        if "jamal washington" in prompt.lower():
            return "NO"
        return "YES"

    out = battery_mod.run_fairness_probes(biased)
    assert out["max_demographic_parity_diff"] == pytest.approx(1.0)


@needs_opsaudit
def test_fairness_probes_fair_target():
    from diligence import battery as battery_mod
    import zlib

    def fair(prompt, context=None):
        return "YES" if zlib.crc32(prompt.encode()) % 2 == 0 else "NO"

    out = battery_mod.run_fairness_probes(fair)
    assert out["max_demographic_parity_diff"] < 0.5


@needs_redteam
def test_redteam_runs_against_callable():
    from diligence import battery as battery_mod
    out = battery_mod.run_redteam(lambda q, context=None: "I can't help.",
                                  "dummy", families=["control"])
    assert out["n_cases"] > 0
    assert 0.0 <= out["overall_pass_rate"] <= 1.0


@needs_aiact
def test_deployer_duties_high_risk_employment():
    from diligence import battery as battery_mod
    out = battery_mod.map_deployer_duties(
        "Screening job applicants for operations analyst roles.",
        "US logistics company", "ScreenBot")
    assert out["tier"] == "high-risk"
    items = [d["item"] for d in out["deployer_duties"]]
    assert any("Deployer obligations" in i for i in items)
    assert any("Fundamental rights" in i for i in items)


def test_lineage_checks_structural():
    from diligence import battery as battery_mod
    rec = {
        "documents": [{"path": "a.md", "status": "present"}],
        "doc_kinds_missing": [],
        "claims": [
            {"category": "training_data_claims", "text": "t1",
             "evidence_doc": "a.md", "evidence_linked": True},
            {"category": "safety_claims", "text": "t2", "evidence_doc": "",
             "evidence_linked": False},
        ],
    }
    out = battery_mod.run_lineage_checks(rec)
    assert out["verification_rate"] == pytest.approx(0.5)
    assert out["claims"][1]["status"] == "unverifiable_no_evidence"


# -- registry (sibling-dependent) ----------------------------------------------

@needs_registry
def test_registry_decision_mapping(tmp_path):
    from diligence import registry as registry_mod
    rec = intake_mod.build_intake(_intake())
    bat = _battery_for()
    for rec_name, score_total, expected in (
            ("go", 90.0, "approved"),
            ("conditional", 60.0, "approved"),
            ("no-go", 20.0, "rejected")):
        sc = {"recommendation": rec_name, "total": score_total,
              "risk_level": "low" if rec_name == "go" else "high",
              "blockers": [] if rec_name != "no-go" else ["x"],
              "dimensions": {
                  "documentation": {"score": 80, "weight": 0.2, "notes": []},
                  "security_robustness": {"score": 80, "weight": 0.25,
                                          "notes": []},
                  "fairness": {"score": 80, "weight": 0.2, "notes": []},
                  "lineage": {"score": 80, "weight": 0.15, "notes": []},
                  "regulatory_fit": {"score": 80, "weight": 0.2, "notes": []}}}
        dec = registry_mod.write_decision(tmp_path / f"{rec_name}.db", rec,
                                          bat, sc, approver="tester")
        assert dec["registry_decision"] == expected, rec_name
        assert dec["diligence_recommendation"] == rec_name
        if rec_name == "conditional":
            assert "CONDITIONS" in dec["approval"]["rationale"]


@pytest.mark.parametrize('tier', [None, '', 'unknown', 'minimal', 'malformed'])
def test_unknown_regulatory_tier_cannot_be_go(tmp_path, tier):
    for d in ('model_card.md', 'data_statement.md', 'evaluation_summary.md', 'safety_policy.md'):
        (tmp_path / d).write_text('x')
    rec = intake_mod.build_intake(_full_docs_intake(), docs_dir=tmp_path)
    result = scoring_mod.score(rec, _battery_for(redteam_rate=1, gap=0, tier=tier))
    assert result['recommendation'] != 'go'
    assert result['dimensions']['regulatory_fit']['score'] == 0
    assert any('review required' in n for n in result['dimensions']['regulatory_fit']['notes'])


def test_missing_regulatory_battery_cannot_be_go(tmp_path):
    for d in ('model_card.md', 'data_statement.md', 'evaluation_summary.md', 'safety_policy.md'):
        (tmp_path / d).write_text('x')
    rec = intake_mod.build_intake(_full_docs_intake(), docs_dir=tmp_path)
    battery = _battery_for(redteam_rate=1, gap=0)
    del battery['deployer_duties']
    assert scoring_mod.score(rec, battery)['recommendation'] == 'conditional'
