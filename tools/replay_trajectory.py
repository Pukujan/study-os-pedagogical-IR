from __future__ import annotations

import argparse
from pathlib import Path

from study_os_pir.console import render_turn_text
from study_os_pir.language import LexicalRegister, validate_lexical_register
from study_os_pir.runtime import (
    AssessmentRegistry,
    ReplayContext,
    ReplayPhase,
    build_renderer_contract,
    mark_turn_rendered,
    start_replay,
    submit_response,
)
from study_os_pir.trajectory import ExperimentalTrajectory


def _load_trajectory(path: Path) -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(path.read_text())


def _load_registry(path: Path) -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(path.read_text())


def _load_context(path: Path) -> ReplayContext:
    return ReplayContext.model_validate_json(path.read_text())


def _load_lexical_register(path: Path) -> LexicalRegister:
    return LexicalRegister.model_validate_json(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an approved experimental PIR trajectory in a local terminal."
    )
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--assessments", type=Path, required=True)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--lexical-register", type=Path)
    args = parser.parse_args()

    trajectory = _load_trajectory(args.trajectory)
    registry = _load_registry(args.assessments)
    context = None if args.context is None else _load_context(args.context)
    lexical_register = (
        None if args.lexical_register is None else _load_lexical_register(args.lexical_register)
    )
    if lexical_register is not None:
        persistent_text = () if context is None else context.persistent_text
        violations = validate_lexical_register(
            trajectory,
            lexical_register,
            persistent_text=persistent_text,
        )
        if violations:
            for violation in violations:
                print(f"Replay blocked: {violation.code.value}: {violation.detail}")
            return 2
    cursor = start_replay(trajectory, registry)

    while cursor.phase != ReplayPhase.EXITED:
        if cursor.phase == ReplayPhase.RENDER:
            contract = build_renderer_contract(trajectory, cursor, context)
            print(render_turn_text(contract))
            print()
            cursor = mark_turn_rendered(trajectory, cursor)
            continue

        response = input("> ").strip()
        if response.lower() in {"q", "quit", "exit"}:
            print("Replay stopped by learner.")
            return 0
        try:
            result = submit_response(trajectory, registry, cursor, response)
        except ValueError as exc:
            print(f"Replay blocked: {exc}")
            return 2
        cursor = result.cursor

    print(f"[slice complete: {cursor.exit_target}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
