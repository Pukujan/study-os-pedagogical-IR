from __future__ import annotations

import argparse
from pathlib import Path

from study_os_pir.console import render_turn_text
from study_os_pir.lexical import (
    ExperimentalLexicalPolicy,
    LexicalViolation,
    validate_lexical_policy,
    validate_rendered_turn,
)
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


def _load_lexical_policy(path: Path) -> ExperimentalLexicalPolicy:
    return ExperimentalLexicalPolicy.model_validate_json(path.read_text())


def _violation_details(violations: tuple[LexicalViolation, ...]) -> str:
    return "; ".join(violation.detail for violation in violations)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an approved experimental PIR trajectory in a local terminal."
    )
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--assessments", type=Path, required=True)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--lexical-policy", type=Path)
    args = parser.parse_args()

    trajectory = _load_trajectory(args.trajectory)
    registry = _load_registry(args.assessments)
    context = None if args.context is None else _load_context(args.context)
    lexical_policy = (
        None if args.lexical_policy is None else _load_lexical_policy(args.lexical_policy)
    )
    if lexical_policy is not None:
        lexical_violations = validate_lexical_policy(trajectory, lexical_policy)
        if lexical_violations:
            details = _violation_details(lexical_violations)
            print(f"Replay blocked: invalid lexical policy: {details}")
            return 2

    cursor = start_replay(trajectory, registry)

    while cursor.phase != ReplayPhase.EXITED:
        if cursor.phase == ReplayPhase.RENDER:
            contract = build_renderer_contract(trajectory, cursor, context)
            text = render_turn_text(contract)
            if lexical_policy is not None:
                lexical_violations = validate_rendered_turn(
                    lexical_policy,
                    contract.step_id,
                    text,
                )
                if lexical_violations:
                    print(
                        "Replay blocked: lexical policy violation: "
                        + _violation_details(lexical_violations)
                    )
                    return 2
            print(text)
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
