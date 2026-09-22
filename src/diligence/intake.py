"""Vendor intake: capture what the vendor says, with hashes.

``diligence intake`` turns the vendor's documentation and claims into a
structured, hashed intake record. Nothing is scored here — this module only
records *what the vendor claims* so later steps can check those claims against
evidence and against the system as delivered.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = (
    "vendor_name",
    "system_name",
    "system_version",
    "intended_use",
    "deployer_context",
)

REQUIRED_DOC_KINDS = (
    "model_card",
    "data_statement",
    "evaluation_summary",
    "safety_policy",
)

CLAIM_FIELDS = (
    "training_data_claims",
    "evaluation_claims",
    "safety_claims",
)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_intake(raw: dict, docs_dir: str | Path | None = None) -> dict:
    """Validate raw intake answers and build the hashed intake record."""
    missing = [f for f in REQUIRED_FIELDS if not str(raw.get(f, "")).strip()]
    if missing:
        raise ValueError(f"intake missing required fields: {', '.join(missing)}")

    docs = []
    doc_kinds_present = set()
    for doc in raw.get("documents", []) or []:
        kind = str(doc.get("kind", "")).strip()
        path = str(doc.get("path", "")).strip()
        entry = {"kind": kind, "path": path, "sha256": None, "bytes": None,
                 "status": "declared"}
        if path:
            p = Path(path)
            if docs_dir and not p.is_absolute():
                p = Path(docs_dir) / p
            if p.exists():
                entry["sha256"] = _sha256_file(p)
                entry["bytes"] = p.stat().st_size
                entry["status"] = "present"
            else:
                entry["status"] = "missing"
        if kind:
            doc_kinds_present.add(kind)
        docs.append(entry)

    claims = []
    for field in CLAIM_FIELDS:
        for claim in raw.get(field, []) or []:
            text = str(claim.get("text", "")).strip()
            evidence = str(claim.get("evidence_doc", "")).strip()
            claims.append({
                "category": field,
                "text": text,
                "evidence_doc": evidence,
                "evidence_linked": bool(evidence) and any(
                    d["path"] == evidence and d["status"] == "present"
                    for d in docs
                ),
            })

    record = {
        "schema": "vendor-diligence-intake/1",
        "created_at": utcnow(),
        "vendor_name": raw["vendor_name"].strip(),
        "system_name": raw["system_name"].strip(),
        "system_version": raw.get("system_version", "").strip(),
        "vendor_contact": str(raw.get("vendor_contact", "")).strip(),
        "intended_use": raw["intended_use"].strip(),
        "deployer_context": raw["deployer_context"].strip(),
        "data_processing": str(raw.get("data_processing", "")).strip(),
        "documents": docs,
        "doc_kinds_present": sorted(doc_kinds_present),
        "doc_kinds_missing": [k for k in REQUIRED_DOC_KINDS
                              if k not in doc_kinds_present],
        "claims": claims,
        "claims_without_evidence": sum(1 for c in claims if not c["evidence_linked"]),
    }
    return record


def save_intake(record: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True))
    return path


def load_intake(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
