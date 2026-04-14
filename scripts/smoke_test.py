#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_SCRIPT_PATH = SCRIPT_DIR / "research_vault.py"
LAUNCHER_SCRIPT_PATH = SCRIPT_DIR / "research_launcher.py"


def run_command(script_path: Path, *args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(proc.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="llm-wiki-research-smoke-") as tmpdir:
        root = Path(tmpdir)
        asset_seed_path = root / "seed-image.png"
        asset_seed_path.write_bytes(b"fake-image-bytes-for-smoke-test")
        prepare_payload = run_command(
            LAUNCHER_SCRIPT_PATH,
            "prepare-session",
            "--topic",
            "Smoke Test Topic",
            "--root-dir",
            str(root),
            "--query",
            "smoke test query",
            "--must-answer",
            "Does the launcher produce packet targets?",
            "--assignment",
            "web-explorer|baseline smoke evidence|Collect one strong baseline web packet for the smoke flow.",
        )
        packet_path = Path(prepare_payload["assignments"][0]["packet_target_path"])
        research_plan_path = Path(prepare_payload["research_plan_path"])
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet.update(
            {
                "summary": "Smoke packet generated through the launcher flow.",
                "sources": [
                    {
                        "source_key": "example-source",
                        "title": "Example Source",
                        "source_url": "https://example.com/source",
                        "quality_grade": "B",
                        "summary": "Example summary",
                        "note_markdown": "## Note\n- Example source body.",
                    },
                    {
                        "source_key": "example-source-2",
                        "title": "Example Source Two",
                        "source_url": "https://example.com/source-2",
                        "source_kind": "academic",
                        "quality_grade": "A",
                        "summary": "Second example summary",
                        "note_markdown": "## Note\n- Second example source body.",
                    },
                ],
                "claims": [
                    {
                        "claim_key": "example-claim",
                        "claim": "Example claim from smoke test.",
                        "confidence": "high",
                        "source_keys": ["example-source", "example-source-2"],
                    }
                ],
                "images": [
                    {
                        "title": "Example Image",
                        "source_url": "https://example.com/gallery/example-image",
                        "asset_file_path": str(asset_seed_path),
                        "caption": "Example image used in the smoke flow.",
                        "creator": "Example Research Museum",
                        "license_name": "CC BY 4.0",
                        "license_url": "https://creativecommons.org/licenses/by/4.0/",
                        "attribution_text": "Example Research Museum",
                        "relevance": "Validates local image asset persistence.",
                        "linked_claim_keys": ["example-claim"],
                        "linked_pages": ["images", "timeline"],
                        "note_markdown": "## Image Note\n- Example local image asset.",
                    }
                ],
            }
        )
        packet_path.write_text(
            json.dumps(
                packet,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        status_before = run_command(
            LAUNCHER_SCRIPT_PATH,
            "status-session",
            "--topic",
            "Smoke Test Topic",
            "--root-dir",
            str(root),
            "--run-id",
            prepare_payload["run_id"],
        )
        packet_payload = run_command(
            LAUNCHER_SCRIPT_PATH,
            "ingest-bundle",
            "--topic",
            "Smoke Test Topic",
            "--root-dir",
            str(root),
            "--run-id",
            prepare_payload["run_id"],
            "--refresh",
        )
        verifier_path = Path(prepare_payload["verifier"]["packet_target_path"])
        verifier_packet = json.loads(verifier_path.read_text(encoding="utf-8"))
        verifier_packet.update(
            {
                "summary": "Verification pass confirms the smoke-test claim from two strong sources.",
                "sources": [
                    {
                        "source_key": "verification-source",
                        "title": "Verification Source",
                        "source_url": "https://example.com/verification",
                        "quality_grade": "B",
                        "summary": "Verification source summary",
                        "note_markdown": "## Verification\n- Confirms the example claim.",
                    }
                ],
                "claims": [
                    {
                        "claim_key": "verified-example-claim",
                        "claim": "Example claim from smoke test.",
                        "confidence": "high",
                        "source_keys": ["verification-source"],
                    }
                ],
            }
        )
        verifier_path.write_text(json.dumps(verifier_packet, ensure_ascii=False, indent=2), encoding="utf-8")
        verifier_ingest = run_command(
            LAUNCHER_SCRIPT_PATH,
            "ingest-bundle",
            "--topic",
            "Smoke Test Topic",
            "--root-dir",
            str(root),
            "--run-id",
            prepare_payload["run_id"],
        )
        status_after = run_command(
            LAUNCHER_SCRIPT_PATH,
            "status-session",
            "--topic",
            "Smoke Test Topic",
            "--root-dir",
            str(root),
            "--run-id",
            prepare_payload["run_id"],
        )
        packaged_state = run_command(
            LAUNCHER_SCRIPT_PATH,
            "finalize-session",
            "--topic",
            "Smoke Test Topic",
            "--root-dir",
            str(root),
            "--run-id",
            prepare_payload["run_id"],
        )
        snapshot_payload = run_command(
            VAULT_SCRIPT_PATH,
            "refresh-topic",
            "--topic",
            "Smoke Test Topic",
            "--root-dir",
            str(root),
        )
        lint_payload = packaged_state["lint"]
        specialist_report_path = Path(snapshot_payload["specialist_report_path"])
        executive_summary_path = Path(snapshot_payload["executive_summary_path"])
        specialist_report = json.loads(specialist_report_path.read_text(encoding="utf-8"))
        image_manifest_path = root / "manifests" / "Smoke-Test-Topic" / "images.jsonl"
        image_rows = [json.loads(line) for line in image_manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not image_rows:
            raise SystemExit("Smoke test failed: no image rows were persisted.")
        local_asset_path = image_rows[0].get("local_asset_path") or ""
        if not local_asset_path:
            raise SystemExit("Smoke test failed: image asset was not saved.")
        persisted_asset_path = root / local_asset_path

        if not lint_payload.get("valid"):
            raise SystemExit(f"Smoke test failed lint: {json.dumps(lint_payload, ensure_ascii=False)}")
        if not research_plan_path.exists():
            raise SystemExit(f"Smoke test failed: research plan missing at {research_plan_path}")
        if not persisted_asset_path.exists():
            raise SystemExit(f"Smoke test failed: persisted image asset missing at {persisted_asset_path}")
        if specialist_report.get("readiness") not in {"usable", "strong"}:
            raise SystemExit(f"Smoke test failed specialist readiness: {json.dumps(specialist_report, ensure_ascii=False)}")
        if not executive_summary_path.exists():
            raise SystemExit(f"Smoke test failed: executive summary missing at {executive_summary_path}")

        result = {
            "ok": True,
            "research_root": root.as_posix(),
            "run_id": prepare_payload["run_id"],
            "planning_stage": prepare_payload["stage"],
            "research_plan_path": prepare_payload["research_plan_path"],
            "status_before": status_before["recommended_next_step"],
            "explorer_packet_id": packet_payload["ingested_packets"][0]["packet_id"],
            "verifier_packet_id": verifier_ingest["ingested_packets"][0]["packet_id"],
            "status_after": status_after["recommended_next_step"],
            "final_stage": packaged_state["run_state"]["stage"],
            "final_status": packaged_state["run_state"]["status"],
            "snapshot_path": snapshot_payload["snapshot_path"],
            "specialist_report_path": snapshot_payload["specialist_report_path"],
            "executive_summary_path": snapshot_payload["executive_summary_path"],
            "specialist_readiness": snapshot_payload["specialist_readiness"],
            "persisted_asset_path": persisted_asset_path.as_posix(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
