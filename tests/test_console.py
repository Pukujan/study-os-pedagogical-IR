from __future__ import annotations

from pathlib import Path

from study_os_pir.console import render_representation_text, render_turn_text
from study_os_pir.runtime import AssessmentRegistry, build_renderer_contract, start_replay
from study_os_pir.trajectory import ExperimentalTrajectory

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "sliding-window-foundations"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(
        (FIXTURE_DIR / "trajectory.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.v0.json").read_text()
    )


def test_representation_without_box_renders_rows_and_annotations() -> None:
    trajectory = load_trajectory()
    representation = next(
        item for item in trajectory.representations if item.representation_id == "r.position_intro"
    )
    text = render_representation_text(representation)
    assert "positions(p)" in text
    assert "numbers(a)" in text
    assert "p = 3 points to a = 2" in text
    assert "box:" not in text


def test_representation_with_box_renders_window_markers() -> None:
    trajectory = load_trajectory()
    representation = next(
        item for item in trajectory.representations if item.representation_id == "r.k_intro"
    )
    text = render_representation_text(representation)
    assert "box" in text
    assert "^^^^^" in text
    assert "k = 3" in text


def test_non_probe_turn_renders_representation_without_question() -> None:
    trajectory = load_trajectory()
    contract = build_renderer_contract(
        trajectory,
        start_replay(trajectory, load_registry()),
    )
    text = render_turn_text(contract)
    assert "numbers(a)" in text
    assert "?" not in text


def test_probe_turn_appends_exact_authorized_question() -> None:
    trajectory = load_trajectory()
    step = next(item for item in trajectory.steps if item.step_id == "position_probe6")
    from study_os_pir.runtime import ReplayCursor, ReplayPhase

    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id=step.step_id,
    )
    text = render_turn_text(build_renderer_contract(trajectory, cursor))
    assert text.endswith("What is position(p) of number(a) 6?")
