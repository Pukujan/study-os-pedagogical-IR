from __future__ import annotations

from pathlib import Path

from study_os_pir.runtime import (
    AssessmentRegistry,
    ReplayContext,
    ReplayPhase,
    build_renderer_contract,
    mark_turn_rendered,
    start_replay,
    validate_assessment_registry,
)
from study_os_pir.trajectory import ExperimentalTrajectory, validate_trajectory
from study_os_pir.vertical import VerticalStepKind

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "final-combined-loop"
TRAJECTORY_PATH = FIXTURE_DIR / "trajectory.replay.v0.json"
ASSESSMENT_PATH = FIXTURE_DIR / "assessments.replay.v0.json"
CONTEXT_PATH = FIXTURE_DIR / "context.replay.v0.json"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(TRAJECTORY_PATH.read_text())


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(ASSESSMENT_PATH.read_text())


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(CONTEXT_PATH.read_text())


def test_probe_free_final_slice_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    registry = load_registry()
    assert registry.assessments == ()
    assert all(step.kind != VerticalStepKind.PROBE for step in trajectory.steps)
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, registry) == ()


def test_final_loop_is_exposed_only_at_authorized_post_bridge_entry() -> None:
    trajectory = load_trajectory()
    cursor = start_replay(trajectory, load_registry())
    contract = build_renderer_contract(trajectory, cursor, load_context())
    assert contract.step_id == "final_loop_exposure"
    assert contract.probe is None
    assert "final_combined_loop" in contract.disclosed_concepts
    assert "mastery_claim" in contract.forbidden_concepts
    surface = "\n".join(
        value
        for row in contract.representation.rows
        for value in row.values
    )
    assert "for x in range(k):" in surface
    assert "S[i] = S[i] + a[i+x]" in surface
    assert "if S[i] > max_sum:" in surface


def test_probe_free_replay_exits_without_outcomes_or_mastery() -> None:
    trajectory = load_trajectory()
    cursor = start_replay(trajectory, load_registry())

    cursor = mark_turn_rendered(trajectory, cursor)
    assert cursor.phase == ReplayPhase.RENDER
    assert cursor.current_step_id == "no_mastery_boundary"
    assert cursor.visited_step_ids == ("final_loop_exposure",)
    assert cursor.outcomes == ()

    boundary = build_renderer_contract(trajectory, cursor, load_context())
    assert "mastery_unproven" in boundary.disclosed_concepts
    assert "mastery_claim" in boundary.forbidden_concepts
    assert boundary.probe is None

    cursor = mark_turn_rendered(trajectory, cursor)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.current_step_id is None
    assert cursor.exit_target == "session_stop_no_mastery"
    assert cursor.visited_step_ids == (
        "final_loop_exposure",
        "no_mastery_boundary",
    )
    assert cursor.outcomes == ()
