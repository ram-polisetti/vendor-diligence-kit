"""CLI: diligence intake | run | score | decide | report | show"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _pkg():
    # Allow running from the repo without installation: add src/ to sys.path.
    here = Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent]:
        src = parent / "src"
        if (src / "diligence").exists() and str(src) not in sys.path:
            sys.path.insert(0, str(src))
    import diligence  # noqa: E402
    return diligence


def _load_target(target_ref: str):
    """Target is ``module.path:attr`` (callable) or an http(s) URL."""
    if target_ref.startswith(("http://", "https://")):
        diligence = _pkg()
        diligence.siblings.import_sibling("rag-redteam")
        from ragredteam.target import HttpTarget
        return HttpTarget(target_ref, name=target_ref), target_ref
    mod_path, _, attr = target_ref.partition(":")
    if not attr:
        raise SystemExit("target must be module.path:attr or an http(s) URL")
    spec = importlib.util.spec_from_file_location("vendor_target", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, attr)
    return fn, target_ref


def cmd_intake(args):
    diligence = _pkg()
    raw = json.loads(Path(args.answers).read_text())
    record = diligence.intake.build_intake(raw, docs_dir=args.docs_dir)
    path = diligence.intake.save_intake(record, args.out)
    missing = record["doc_kinds_missing"]
    print(f"intake written to {path}")
    print(f"vendor: {record['vendor_name']} / {record['system_name']}")
    if missing:
        print(f"WARNING: missing document kinds: {', '.join(missing)}")
    print(f"claims without evidence: {record['claims_without_evidence']}")


def cmd_run(args):
    diligence = _pkg()
    intake = diligence.intake.load_intake(args.intake)
    target_fn, target_name = _load_target(args.target)
    families = args.families.split(",") if args.families else None
    battery = diligence.battery.run_battery(intake, target_fn, target_name,
                                            redteam_families=families)
    path = diligence.battery.save_battery(battery, args.out)
    rt = battery["redteam"]
    print(f"battery written to {path}")
    print(f"red-team pass rate: {(rt.get('overall_pass_rate') or 0.0):.1%} "
          f"({'MET' if rt.get('met_threshold') else 'NOT MET'})")
    print(f"fairness max parity gap: "
          f"{battery['fairness'].get('max_demographic_parity_diff')}")
    print(f"lineage verification rate: "
          f"{(battery['lineage'].get('verification_rate') or 0.0):.0%}")
    print(f"EU AI Act tier: {battery['deployer_duties'].get('tier')}")
    for w in battery.get("sibling_warnings", []):
        print(f"WARNING: {w}")


def cmd_score(args):
    diligence = _pkg()
    intake = diligence.intake.load_intake(args.intake)
    battery = json.loads(Path(args.battery).read_text())
    score = diligence.scoring.score(intake, battery)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(score, indent=2, sort_keys=True))
    print(f"score written to {out}")
    print(f"total: {score['total']}/100 -> {score['recommendation'].upper()} "
          f"(risk: {score['risk_level']})")
    for b in score["blockers"]:
        print(f"BLOCKER: {b}")


def cmd_decide(args):
    diligence = _pkg()
    intake = diligence.intake.load_intake(args.intake)
    battery = json.loads(Path(args.battery).read_text())
    score = json.loads(Path(args.score).read_text())
    decision = diligence.registry.write_decision(
        args.registry, intake, battery, score,
        approver=args.approver, actor=args.actor)
    print(f"registry: {args.registry}")
    print(f"system: {decision['system']}")
    print(f"diligence recommendation: {decision['diligence_recommendation']}")
    print(f"registry decision: {decision['registry_decision']}")
    if args.seal:
        sealed = _try_seal(args, decision, intake, battery, score)
        print(sealed)
    Path(args.out).write_text(json.dumps(decision, indent=2, sort_keys=True,
                                         default=str))
    print(f"decision written to {args.out}")


def _try_seal(args, decision: dict, intake: dict, battery: dict,
              score: dict) -> str:
    diligence = _pkg()
    if not args.pack:
        return ("vault sealing skipped: no --pack given (vault build requires "
                "a conformance pack; pass --pack <dir> to seal)")
    try:
        diligence.siblings.import_sibling("governance-evidence-vault")
    except ImportError as exc:
        return f"vault sealing skipped: {exc}"
    from govault import cli as vault_cli
    out_dir = Path(args.out).parent
    bundle_dir = out_dir / "sealed-bundle"
    # Stage the diligence artifacts as --extra inputs for the vault.
    staged = out_dir / "vault-inputs"
    staged.mkdir(parents=True, exist_ok=True)
    extras = []
    for kind, payload in (("diligence-intake", {"intake": intake}),
                          ("diligence-battery", {"battery": battery}),
                          ("diligence-score", {"score": score}),
                          ("diligence-decision", decision)):
        p = staged / f"{kind}.json"
        p.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
        extras += ["--extra", f"{kind}:{p}"]
    argv = (["build", "--system", decision["system"],
             "--pack", args.pack, "--registry", args.registry,
             "--out", str(bundle_dir)] + extras)
    if args.vault_key:
        argv += ["--key", args.vault_key]
    try:
        rc = vault_cli.main(argv)
    except SystemExit as exc:
        rc = exc.code
    if rc == 0:
        return f"sealed vault bundle at {bundle_dir}"
    return f"vault sealing failed (exit {rc}) — diligence record unaffected"


def cmd_report(args):
    diligence = _pkg()
    intake = diligence.intake.load_intake(args.intake)
    battery = json.loads(Path(args.battery).read_text())
    score = json.loads(Path(args.score).read_text())
    decision = None
    if args.decision:
        decision = json.loads(Path(args.decision).read_text())
    paths = diligence.report.write_report(intake, battery, score, args.out,
                                          decision)
    print(f"report: {paths['markdown']}")
    print(f"bundle: {paths['json']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="diligence",
                                 description="Third-party AI vendor diligence kit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("intake", help="capture vendor docs and claims")
    p.add_argument("--answers", required=True, help="JSON file with intake answers")
    p.add_argument("--docs-dir", default=None, help="base dir for document paths")
    p.add_argument("--out", default="intake.json")
    p.set_defaults(fn=cmd_intake)

    p = sub.add_parser("run", help="run the test battery against the vendor target")
    p.add_argument("--intake", required=True)
    p.add_argument("--target", required=True,
                   help="module.path:attr returning a callable, or http(s) URL")
    p.add_argument("--families", default=None,
                   help="comma-separated red-team families (default: all)")
    p.add_argument("--out", default="battery.json")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("score", help="score the battery results")
    p.add_argument("--intake", required=True)
    p.add_argument("--battery", required=True)
    p.add_argument("--out", default="score.json")
    p.set_defaults(fn=cmd_score)

    p = sub.add_parser("decide", help="write the go/no-go into the registry")
    p.add_argument("--intake", required=True)
    p.add_argument("--battery", required=True)
    p.add_argument("--score", required=True)
    p.add_argument("--registry", required=True, help="registry sqlite path")
    p.add_argument("--approver", required=True)
    p.add_argument("--actor", default="diligence-kit")
    p.add_argument("--seal", action="store_true",
                   help="also seal the bundle with the evidence vault if available")
    p.add_argument("--pack", default=None,
                   help="conformance-pack dir (required for --seal)")
    p.add_argument("--vault-key", default=None,
                   help="HMAC key file for the vault attestation signature")
    p.add_argument("--out", default="decision.json")
    p.set_defaults(fn=cmd_decide)

    p = sub.add_parser("report", help="render the diligence report")
    p.add_argument("--intake", required=True)
    p.add_argument("--battery", required=True)
    p.add_argument("--score", required=True)
    p.add_argument("--decision", default=None)
    p.add_argument("--out", default="report")
    p.set_defaults(fn=cmd_report)

    args = ap.parse_args(argv)
    args.fn(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
