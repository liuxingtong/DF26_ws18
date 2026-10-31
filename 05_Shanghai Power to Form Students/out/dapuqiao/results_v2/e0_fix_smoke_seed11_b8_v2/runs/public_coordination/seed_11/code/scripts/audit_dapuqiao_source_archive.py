#!/usr/bin/env python3
"""Validate the cross-round Dapuqiao source archive and legacy freeze manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "dapuqiao" / "SOURCE_ARCHIVE.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hashes(base: Path, records: dict[str, str]) -> list[dict]:
    results = []
    for relative, expected in records.items():
        path = base / relative
        actual = sha256(path) if path.exists() else None
        results.append({
            "file": relative,
            "exists": path.exists(),
            "matches": actual == expected,
            "expected_sha256": expected,
            "actual_sha256": actual,
        })
    return results


def main() -> int:
    archive = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    results = check_hashes(ROOT, archive["files"])

    review_manifest_path = ROOT / "review_app" / "public" / "data" / "FREEZE_MANIFEST.json"
    review_manifest = json.loads(review_manifest_path.read_text(encoding="utf-8"))
    review_results = check_hashes(review_manifest_path.parent, review_manifest["files"])

    formal_path = ROOT / "data" / "dapuqiao" / "formal_input_quality.json"
    formal = json.loads(formal_path.read_text(encoding="utf-8"))
    formal_results = check_hashes(formal_path.parent, formal["sha256"])

    round_records = sorted({
        item
        for update in archive["update_rounds"]
        for item in update["record_files"]
    })
    missing_round_records = [item for item in round_records if not (ROOT / item).exists()]
    ok = (
        all(item["matches"] for item in results)
        and all(item["matches"] for item in review_results)
        and all(item["matches"] for item in formal_results)
        and not missing_round_records
    )
    print(json.dumps({
        "ok": ok,
        "archive_file_count": len(results),
        "archive_hash_matches": sum(item["matches"] for item in results),
        "review_manifest_hash_matches": sum(item["matches"] for item in review_results),
        "review_manifest_file_count": len(review_results),
        "formal_manifest_hash_matches": sum(item["matches"] for item in formal_results),
        "formal_manifest_file_count": len(formal_results),
        "update_round_count": len(archive["update_rounds"]),
        "missing_update_records": missing_round_records,
        "raw_source_payloads_embedded": archive["status"]["raw_commercial_source_files_embedded"],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
