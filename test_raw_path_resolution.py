from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import research_launcher as rl
import research_vault as rv


def test_start_research_run_uses_entity_slug_for_raw_directory(tmp_path):
    payload = rv.start_research_run(
        "우주 여행의 역사",
        run_id="run1",
        topic_slug="우주_여행의_역사",
        entity_slug="우주_여행",
        section_slug="역사",
        vault_dir=tmp_path,
    )

    run_dir = tmp_path / "raw" / "우주_여행" / "run1"
    assert run_dir.exists()
    assert payload["run_dir"] == str(run_dir)


def test_existing_run_dir_falls_back_to_legacy_topic_slug_path(tmp_path):
    legacy_run_dir = tmp_path / "raw" / "우주_여행의_역사" / "run1"
    legacy_run_dir.mkdir(parents=True)

    paths = rv.resolve_topic_paths(
        "우주 여행의 역사",
        topic_slug="우주_여행의_역사",
        entity_slug="우주_여행",
        vault_dir=tmp_path,
    )

    resolved = rv._existing_run_dir(paths, "run1")
    assert resolved == legacy_run_dir


def test_prepare_session_records_entity_slug_and_raw_slug(tmp_path):
    payload = rl.prepare_session(
        topic="우주 여행의 역사",
        query="우주 여행의 역사",
        run_id="run1",
        topic_slug="우주_여행의_역사",
        entity_slug="우주_여행",
        section_slug="역사",
        vault_dir=tmp_path,
        downstream_use="youtube-script",
        must_answer=[],
        excluded_scope=[],
        notes="",
        custom_assignments=[],
    )

    assert payload["entity_slug"] == "우주_여행"
    assert payload["raw_slug"] == "우주_여행"
    assert Path(payload["bundle_dir"]).exists()

    plan_path = Path(payload["session_plan_path"])
    assert plan_path.exists()
    text = plan_path.read_text(encoding="utf-8")
    assert '"entity_slug": "우주_여행"' in text
    assert '"section_slug": "역사"' in text
    assert '"raw_slug": "우주_여행"' in text


def test_research_vault_cli_start_run_accepts_entity_slug(tmp_path):
    parser = rv.build_parser()
    args = parser.parse_args([
        "start-run",
        "--topic",
        "우주 여행의 역사",
        "--topic-slug",
        "우주_여행의_역사",
        "--entity-slug",
        "우주_여행",
        "--section-slug",
        "역사",
    ])

    assert args.entity_slug == "우주_여행"
    assert args.section_slug == "역사"
