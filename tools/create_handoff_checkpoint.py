from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
CURRENT_PATH = ROOT / "assurance" / "HANDOFF_STATE.json"
CHECKPOINT_DIR = ROOT / "assurance" / "checkpoints"
ALLOWED_REASONS = {
    "session_end",
    "agent_transfer",
    "repository_transfer",
    "pr_transition",
    "validation_transition",
    "milestone_transition",
    "blocked",
    "next_action_changed",
    "material_plan_change",
}


def _object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    return cast(dict[str, Any], value)


def create_checkpoint(*, name: str, created_at: str, reason: str) -> Path:
    if not name or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in name):
        raise ValueError("name must contain only lowercase letters, digits, and hyphens")
    if reason not in ALLOWED_REASONS:
        raise ValueError(f"unsupported PAM handoff reason: {reason}")
    state = _object(json.loads(CURRENT_PATH.read_text(encoding="utf-8")), "current handoff")
    if state.get("schema_version") != "pam-handoff/0.2.0":
        raise ValueError("current handoff must use pam-handoff/0.2.0")
    if state.get("state_kind") != "current":
        raise ValueError("assurance/HANDOFF_STATE.json must have state_kind=current")
    handoff = _object(state.get("handoff"), "current handoff.handoff")
    state["state_kind"] = "historical_checkpoint"
    handoff["created_at"] = created_at
    handoff["reason"] = reason
    target = CHECKPOINT_DIR / f"{name}.json"
    if target.exists():
        raise FileExistsError(f"checkpoint already exists: {target.relative_to(ROOT)}")
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an immutable PAM historical checkpoint.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--reason", default="milestone_transition", choices=sorted(ALLOWED_REASONS))
    args = parser.parse_args()
    target = create_checkpoint(name=args.name, created_at=args.created_at, reason=args.reason)
    print(f"created {target.relative_to(ROOT)}")
    print("run `make docs-sync` and commit the checkpoint plus generated documentation")


if __name__ == "__main__":
    main()
