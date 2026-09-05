from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "docs" / "repository-state.json"
HANDOFF_PATH = ROOT / "assurance" / "HANDOFF_STATE.json"
CHECKPOINT_DIR = ROOT / "assurance" / "checkpoints"
README_PATH = ROOT / "README.md"
STATUS_PATH = ROOT / "docs" / "STATUS.md"
README_START = "<!-- BEGIN GENERATED PROJECT STATUS -->"
README_END = "<!-- END GENERATED PROJECT STATUS -->"
README_ANCHOR = "## Repository boundary"


def _object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    return cast(dict[str, Any], value)


def _string(mapping: dict[str, Any], key: str, name: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}.{key} must be a non-empty string")
    return value


def _string_list(mapping: dict[str, Any], key: str, name: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{name}.{key} must be a list of strings")
    return tuple(cast(list[str], value))


def _load_json(path: Path) -> dict[str, Any]:
    return _object(json.loads(path.read_text(encoding="utf-8")), path.as_posix())


def _checkpoint_paths() -> tuple[Path, ...]:
    if not CHECKPOINT_DIR.exists():
        return ()
    return tuple(sorted(path for path in CHECKPOINT_DIR.glob("*.json") if path.is_file()))


def _generated_note() -> str:
    return (
        "> Generated from `docs/repository-state.json`, the PAM current handoff, and historical "
        "checkpoints. Run `make docs-sync` after changing those inputs. `make docs-check` fails on "
        "drift. Design specs remain human-reviewed."
    )


def _phase(handoff: dict[str, Any]) -> str:
    project = _object(handoff.get("project"), "handoff.project")
    return _string(project, "phase", "handoff.project")


def _next_action(handoff: dict[str, Any]) -> str:
    next_action = _object(handoff.get("next_action"), "handoff.next_action")
    return _string(next_action, "action", "handoff.next_action")


def _blockers(handoff: dict[str, Any]) -> tuple[str, ...]:
    value = handoff.get("blockers")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError("handoff.blockers must be a list of strings")
    return tuple(cast(list[str], value))


def _validation_names(handoff: dict[str, Any]) -> tuple[str, ...]:
    validation = _object(handoff.get("validation"), "handoff.validation")
    passed = validation.get("passed")
    if not isinstance(passed, list):
        raise TypeError("handoff.validation.passed must be a list")
    names: list[str] = []
    for index, item in enumerate(passed):
        entry = _object(item, f"handoff.validation.passed[{index}]")
        names.append(_string(entry, "name", f"handoff.validation.passed[{index}]"))
    return tuple(names)


def _evidence_lines(state: dict[str, Any]) -> tuple[str, ...]:
    evidence = _object(state.get("evidence"), "repository-state.evidence")
    required = {
        "sep4_total_turns": "September-4 turns accounted",
        "sep4_learner_turns": "learner turns",
        "sep4_tutor_turns": "tutor turns",
        "sep4_candidate_events": "candidate pedagogical events",
        "sep4_failure_repair_regions": "failure/repair regions",
        "sep4_unresolved_questions": "retained unresolved questions",
    }
    lines: list[str] = []
    for key, label in required.items():
        value = evidence.get(key)
        if not isinstance(value, int) or value < 0:
            raise TypeError(f"repository-state.evidence.{key} must be a non-negative integer")
        lines.append(f"- {label}: **{value}**")
    return tuple(lines)


def render_readme_block(state: dict[str, Any], handoff: dict[str, Any]) -> str:
    label = _string(state, "program_label", "repository-state")
    stability = _string(state, "stability", "repository-state")
    landed = _string_list(state, "landed_capabilities", "repository-state")
    not_proven = _string_list(state, "not_yet_proven", "repository-state")
    checkpoints = _checkpoint_paths()
    lines = [
        README_START,
        "## Current project status",
        "",
        _generated_note(),
        "",
        f"- Program: **{label}**",
        f"- Stability: **{stability}**",
        f"- Current phase: **{_phase(handoff)}**",
        f"- Historical checkpoints: **{len(checkpoints)}**",
        "",
        "### Landed and tested capabilities",
        "",
        *[f"- {item}" for item in landed],
        "",
        "### Current next action",
        "",
        _next_action(handoff),
        "",
        "### Not yet proven",
        "",
        *[f"- {item}" for item in not_proven],
        README_END,
    ]
    return "\n".join(lines)


def render_status(state: dict[str, Any], handoff: dict[str, Any]) -> str:
    landed = _string_list(state, "landed_capabilities", "repository-state")
    not_proven = _string_list(state, "not_yet_proven", "repository-state")
    checkpoint_paths = _checkpoint_paths()
    checkpoint_lines = [f"- `{path.relative_to(ROOT).as_posix()}`" for path in checkpoint_paths]
    if not checkpoint_lines:
        checkpoint_lines = ["- none"]
    lines = [
        "# Study OS PIR — Current Status",
        "",
        _generated_note(),
        "",
        "## Current phase",
        "",
        _phase(handoff),
        "",
        "## Evidence snapshot",
        "",
        *_evidence_lines(state),
        "",
        "## Landed and tested capabilities",
        "",
        *[f"- {item}" for item in landed],
        "",
        "## Current validation receipts",
        "",
        *[f"- {item}" for item in _validation_names(handoff)],
        "",
        "## Current next action",
        "",
        _next_action(handoff),
        "",
        "## Current blockers",
        "",
        *[f"- {item}" for item in _blockers(handoff)],
        "",
        "## Not yet proven",
        "",
        *[f"- {item}" for item in not_proven],
        "",
        "## Historical PAM checkpoints",
        "",
        *checkpoint_lines,
        "",
        "Historical checkpoints are immutable observations. Live repository and CI state wins when "
        "a checkpoint becomes stale.",
        "",
    ]
    return "\n".join(lines)


def _replace_block(text: str, block: str) -> str:
    start_count = text.count(README_START)
    end_count = text.count(README_END)
    if start_count != end_count or start_count > 1:
        raise ValueError("README generated status markers must be absent or appear exactly once")
    if start_count == 1:
        start = text.index(README_START)
        end = text.index(README_END, start) + len(README_END)
        return text[:start] + block + text[end:]
    if README_ANCHOR not in text:
        raise ValueError(f"README is missing insertion anchor {README_ANCHOR!r}")
    return text.replace(README_ANCHOR, f"{block}\n\n{README_ANCHOR}", 1)


def expected_documents() -> dict[Path, str]:
    state = _load_json(STATE_PATH)
    if state.get("schema_version") != "study-os-pir-repository-state/1.0.0":
        raise ValueError("unsupported repository-state schema_version")
    handoff = _load_json(HANDOFF_PATH)
    if handoff.get("schema_version") != "pam-handoff/0.2.0":
        raise ValueError("HANDOFF_STATE.json must use pam-handoff/0.2.0")
    if handoff.get("state_kind") != "current":
        raise ValueError("HANDOFF_STATE.json must remain the current handoff")
    readme = README_PATH.read_text(encoding="utf-8")
    return {
        README_PATH: _replace_block(readme, render_readme_block(state, handoff)),
        STATUS_PATH: render_status(state, handoff),
    }


def sync_documents(*, write: bool) -> tuple[str, ...]:
    stale: list[str] = []
    for path, expected in expected_documents().items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current == expected:
            continue
        stale.append(path.relative_to(ROOT).as_posix())
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    return tuple(stale)


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize durable project status into docs.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    stale = sync_documents(write=bool(args.write))
    if args.check and stale:
        paths = "\n- ".join(stale)
        raise SystemExit(
            "generated project documentation is stale; run `make docs-sync` and commit:\n- "
            + paths
        )
    if args.write:
        if stale:
            message = "synchronized: " + ", ".join(stale)
        else:
            message = "documentation already synchronized"
        print(message)
    else:
        print("documentation synchronization: PASS")


if __name__ == "__main__":
    main()
