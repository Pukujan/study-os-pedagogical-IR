from __future__ import annotations

from pathlib import Path

from study_os_pir.language import (
    LexicalRegister,
    LexicalViolationCode,
    validate_lexical_register,
)
from study_os_pir.runtime import (
    AssessmentRegistry,
    ReplayContext,
    ReplayCursor,
    ReplayPhase,
    build_renderer_contract,
    mark_turn_rendered,
    start_replay,
    submit_response,
    validate_assessment_registry,
)
from study_os_pir.trajectory import (
    ExperimentalTrajectory,
    TrajectoryOutcomeKind,
    validate_trajectory,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "arbitrary-k-first-window"
TRAJECTORY_PATH = FIXTURE_DIR / "trajectory.replay.v0.json"
ASSESSMENT_PATH = FIXTURE_DIR / "assessments.replay.v0.json"
CONTEXT_PATH = FIXTURE_DIR / "context.replay.v0.json"
REGISTER_PATH = FIXTURE_DIR / "register.preserve-s.v0.json"
PROBLEM_TEXT = "Find the largest sum of any k numbers next to each other in the array."


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(TRAJECTORY_PATH.read_text())


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(ASSESSMENT_PATH.read_text())


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(CONTEXT_PATH.read_text())


def load_register() -> LexicalRegister:
    return LexicalRegister.model_validate_json(REGISTER_PATH.read_text())


def render_until_blocked(cursor: ReplayCursor) -> ReplayCursor:
    trajectory = load_trajectory()
    current = cursor
    while current.phase == ReplayPhase.RENDER:
        build_renderer_contract(trajectory, current, load_context())
        current = mark_turn_rendered(trajectory, current)
    return current


def response_then_render(
    cursor: ReplayCursor,
    response: str,
) -> tuple[TrajectoryOutcomeKind, ReplayCursor]:
    result = submit_response(load_trajectory(), load_registry(), cursor, response)
    return result.outcome, render_until_blocked(result.cursor)


def render_cursor(step_id: str) -> ReplayCursor:
    return ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=load_trajectory().trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id=step_id,
    )


def test_arbitrary_k_fixture_is_runtime_and_lexically_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()
    assert (
        validate_lexical_register(
            trajectory,
            load_register(),
            persistent_text=load_context().persistent_text,
        )
        == ()
    )


def test_replay_reaches_inner_loop_probe_without_exposing_final_loop() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.phase == ReplayPhase.AWAIT_RESPONSE
    assert cursor.current_step_id == "inner_loop_probe"
    assert cursor.visited_step_ids == (
        "preserve_existing_s",
        "seed_same_s",
        "range_k_bridge",
        "range_contrast_bridge",
        "inner_loop_probe",
    )
    contract = build_renderer_contract(
        load_trajectory(),
        render_cursor("inner_loop_probe"),
        load_context(),
    )
    assert contract.probe is not None
    learner_surface = "\n".join(
        (*contract.representation.annotations, contract.probe.prompt)
    )
    assert "S[i] = S[i] + a[i+x]" not in learner_surface
    assert "complete combined loop" not in learner_surface


def test_source_shaped_append_inside_x_is_partial_then_repairs_same_s_only() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    outcome, cursor = response_then_render(
        cursor,
        "for x in range(k):\n    s.append(???",
    )
    assert outcome == TrajectoryOutcomeKind.PARTIAL
    assert "append_inside_correction" in cursor.visited_step_ids
    assert cursor.current_step_id == "inner_loop_retry_probe"
    assert cursor.phase == ReplayPhase.AWAIT_RESPONSE

    outcome, cursor = response_then_render(
        cursor,
        "for x in range(k):\n    s[i] = s[i] + a[i+x]",
    )
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "final_combined_loop_exposure"
    assert cursor.visited_step_ids[-4:] == (
        "render_x0_state",
        "render_x1_state",
        "render_x2_state",
        "inner_loop_validate",
    )


def test_correct_inner_loop_skips_append_repair_and_renders_state_trace() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    outcome, cursor = response_then_render(
        cursor,
        "for x in range(k):\n    S[i] = S[i] + a[i+x]",
    )
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert "append_inside_correction" not in cursor.visited_step_ids
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "final_combined_loop_exposure"


def test_each_x_state_keeps_i_k_box_and_current_s_visible() -> None:
    expected = {
        "render_x0_state": ("x = 0", "S[i] = 0", "S[i]: 0 + 2 -> 2"),
        "render_x1_state": ("x = 1", "S[i] = 2", "S[i]: 2 + 6 -> 8"),
        "render_x2_state": ("x = 2", "S[i] = 8", "S[i]: 8 + 4 -> 12"),
    }
    for step_id, literals in expected.items():
        contract = build_renderer_contract(
            load_trajectory(),
            render_cursor(step_id),
            load_context(),
        )
        assert contract.representation.box is not None
        assert contract.representation.box.start_index == 0
        assert contract.representation.box.width == 3
        surface = "\n".join(contract.representation.annotations)
        assert "i = 0" in surface
        assert "k = 3" in surface
        for literal in literals:
            assert literal in surface


def sum_identifier_mutation() -> ExperimentalTrajectory:
    trajectory = load_trajectory()
    target = next(
        representation
        for representation in trajectory.representations
        if representation.representation_id == "r.seed_s"
    )
    mutated_representation = target.model_copy(
        update={
            "annotations": tuple(
                "sum = 0" if annotation == "S.append(0)" else annotation
                for annotation in target.annotations
            )
        }
    )
    representations = tuple(
        mutated_representation
        if representation.representation_id == target.representation_id
        else representation
        for representation in trajectory.representations
    )
    return trajectory.model_copy(update={"representations": representations})


def window_sum_identifier_mutation() -> ExperimentalTrajectory:
    trajectory = load_trajectory()
    target = next(
        representation
        for representation in trajectory.representations
        if representation.representation_id == "r.seed_s"
    )
    mutated_representation = target.model_copy(
        update={
            "annotations": tuple(
                "window_sum = 0" if annotation == "S.append(0)" else annotation
                for annotation in target.annotations
            )
        }
    )
    representations = tuple(
        mutated_representation
        if representation.representation_id == target.representation_id
        else representation
        for representation in trajectory.representations
    )
    return trajectory.model_copy(update={"representations": representations})


def test_existing_lexical_register_rejects_window_sum_alias_semantics_miss() -> None:
    mutated = window_sum_identifier_mutation()
    assert validate_trajectory(mutated) == ()
    violations = validate_lexical_register(
        mutated,
        load_register(),
        persistent_text=load_context().persistent_text,
    )
    assert any(
        violation.code == LexicalViolationCode.FORBIDDEN_TERM_PRESENT
        and "'window_sum'" in violation.detail
        for violation in violations
    )


def test_source_rejected_sum_identifier_falsifies_global_term_scope() -> None:
    mutated = sum_identifier_mutation()
    assert validate_trajectory(mutated) == ()
    assert (
        validate_lexical_register(
            mutated,
            load_register(),
            persistent_text=load_context().persistent_text,
        )
        == ()
    )

    register = load_register()
    sum_rule = register.rules[0].model_copy(
        update={"forbidden_terms": (*register.rules[0].forbidden_terms, "sum")}
    )
    strict_register = register.model_copy(
        update={"rules": (sum_rule, *register.rules[1:])}
    )
    violations = validate_lexical_register(
        load_trajectory(),
        strict_register,
        persistent_text=(PROBLEM_TEXT,),
    )
    assert any(
        violation.code == LexicalViolationCode.FORBIDDEN_TERM_PRESENT
        and "'sum'" in violation.detail
        for violation in violations
    )
