from __future__ import annotations

from pathlib import Path

import pytest

from study_os_pir.trajectory import (
    AutomaticTransition,
    ExperimentalTrajectory,
    OutcomeRoute,
    TrajectoryOutcomeKind,
    TrajectoryViolationCode,
    simulate_trajectory,
    validate_trajectory,
)
from study_os_pir.vertical import VerticalStepKind

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    ROOT
    / "fixtures"
    / "public"
    / "sliding-window-foundations"
    / "trajectory.v0.json"
)


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(FIXTURE.read_text())


def violation_codes(trajectory: ExperimentalTrajectory) -> tuple[TrajectoryViolationCode, ...]:
    return tuple(violation.code for violation in validate_trajectory(trajectory))


def replace_step(
    trajectory: ExperimentalTrajectory,
    step_id: str,
    **updates: object,
) -> ExperimentalTrajectory:
    steps = tuple(
        step.model_copy(update=updates) if step.step_id == step_id else step
        for step in trajectory.steps
    )
    return trajectory.model_copy(update={"steps": steps})


def replace_representation(
    trajectory: ExperimentalTrajectory,
    representation_id: str,
    **updates: object,
) -> ExperimentalTrajectory:
    representations = tuple(
        representation.model_copy(update=updates)
        if representation.representation_id == representation_id
        else representation
        for representation in trajectory.representations
    )
    return trajectory.model_copy(update={"representations": representations})


def test_foundations_branching_trajectory_is_valid() -> None:
    assert validate_trajectory(load_trajectory()) == ()


def test_simulation_pauses_at_first_probe_without_outcome() -> None:
    simulation = simulate_trajectory(load_trajectory(), ())
    assert simulation.visited_step_ids == (
        "problem_anchor",
        "position_intro",
        "position_probe6",
    )
    assert simulation.consumed_outcomes == ()
    assert simulation.awaiting_step_id == "position_probe6"
    assert simulation.exit_target is None


def test_incorrect_position_branch_repairs_retries_and_rejoins_before_index() -> None:
    simulation = simulate_trajectory(
        load_trajectory(),
        (
            TrajectoryOutcomeKind.INCORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
        ),
    )
    assert simulation.exit_target == "i_moves_box"
    assert simulation.awaiting_step_id is None
    assert "position_correct6_wrong" in simulation.visited_step_ids
    assert "position_retry9" in simulation.visited_step_ids
    assert "position_validate9" in simulation.visited_step_ids
    assert "position_confirm7" in simulation.visited_step_ids
    assert simulation.visited_step_ids.index("position_validate7") < simulation.visited_step_ids.index(
        "index_intro"
    )
    assert simulation.visited_step_ids.index("index_validate9") < simulation.visited_step_ids.index(
        "k_intro"
    )
    assert simulation.visited_step_ids.index("k_validate5") == len(simulation.visited_step_ids) - 1


def test_initial_correct_position_branch_skips_error_only_retry() -> None:
    simulation = simulate_trajectory(
        load_trajectory(),
        (
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
            TrajectoryOutcomeKind.CORRECT,
        ),
    )
    assert simulation.exit_target == "i_moves_box"
    assert "position_validate6_correct" in simulation.visited_step_ids
    assert "position_correct6_wrong" not in simulation.visited_step_ids
    assert "position_retry9" not in simulation.visited_step_ids


def test_unmodeled_repeated_error_fails_instead_of_inventing_retry_policy() -> None:
    with pytest.raises(
        ValueError,
        match="no route for outcome incorrect after position_retry9",
    ):
        simulate_trajectory(
            load_trajectory(),
            (TrajectoryOutcomeKind.INCORRECT, TrajectoryOutcomeKind.INCORRECT),
        )


def test_probe_can_exit_directly_when_policy_explicitly_models_that_route() -> None:
    trajectory = load_trajectory()
    probe = next(step for step in trajectory.steps if step.step_id == "position_probe6")
    representation = next(
        representation
        for representation in trajectory.representations
        if representation.representation_id == probe.representation_id
    )
    direct_exit = ExperimentalTrajectory(
        schema_version="pir.experimental-trajectory.v0",
        trajectory_id="synthetic.direct-probe-exit",
        source_locator="synthetic:test",
        entry_step_id=probe.step_id,
        representations=(representation,),
        steps=(probe,),
        automatic_transitions=(),
        outcome_routes=(
            OutcomeRoute(
                route_id="route.exit",
                after_step_id=probe.step_id,
                outcome=TrajectoryOutcomeKind.META,
                next_step_id=None,
                exit_target="done",
                evidence_turn_refs=("synthetic",),
            ),
        ),
    )
    assert validate_trajectory(direct_exit) == ()
    simulation = simulate_trajectory(direct_exit, (TrajectoryOutcomeKind.META,))
    assert simulation.exit_target == "done"


def test_invalid_trajectory_cannot_be_simulated() -> None:
    trajectory = load_trajectory().model_copy(update={"entry_step_id": "missing"})
    with pytest.raises(ValueError, match="cannot simulate invalid trajectory"):
        simulate_trajectory(trajectory, ())


def test_duplicate_step_id_is_rejected() -> None:
    trajectory = load_trajectory()
    duplicate = trajectory.steps[0].model_copy(update={"goal": "duplicate"})
    mutated = trajectory.model_copy(update={"steps": (*trajectory.steps, duplicate)})
    assert TrajectoryViolationCode.DUPLICATE_STEP_ID in violation_codes(mutated)


def test_duplicate_representation_id_is_rejected() -> None:
    trajectory = load_trajectory()
    duplicate = trajectory.representations[0].model_copy(update={"annotations": ("duplicate",)})
    mutated = trajectory.model_copy(
        update={"representations": (*trajectory.representations, duplicate)}
    )
    assert TrajectoryViolationCode.DUPLICATE_REPRESENTATION_ID in violation_codes(mutated)


def test_duplicate_automatic_transition_id_is_rejected() -> None:
    trajectory = load_trajectory()
    duplicate = trajectory.automatic_transitions[0].model_copy(
        update={"from_step_id": "position_intro"}
    )
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (*trajectory.automatic_transitions, duplicate)}
    )
    assert TrajectoryViolationCode.DUPLICATE_AUTO_TRANSITION_ID in violation_codes(mutated)


def test_duplicate_outcome_route_id_is_rejected() -> None:
    trajectory = load_trajectory()
    duplicate = trajectory.outcome_routes[0].model_copy(
        update={"after_step_id": "position_retry9"}
    )
    mutated = trajectory.model_copy(update={"outcome_routes": (*trajectory.outcome_routes, duplicate)})
    assert TrajectoryViolationCode.DUPLICATE_OUTCOME_ROUTE_ID in violation_codes(mutated)


def test_unknown_entry_marks_graph_invalid_and_steps_unreachable() -> None:
    mutated = load_trajectory().model_copy(update={"entry_step_id": "missing"})
    codes = violation_codes(mutated)
    assert TrajectoryViolationCode.UNKNOWN_ENTRY_STEP in codes
    assert TrajectoryViolationCode.UNREACHABLE_STEP in codes


def test_unknown_representation_is_rejected() -> None:
    mutated = replace_step(load_trajectory(), "problem_anchor", representation_id="missing")
    assert TrajectoryViolationCode.UNKNOWN_REPRESENTATION in violation_codes(mutated)


def test_missing_preserved_representation_is_rejected() -> None:
    trajectory = load_trajectory()
    step = next(step for step in trajectory.steps if step.step_id == "position_probe6")
    mutated = replace_step(
        trajectory,
        step.step_id,
        preserve_components=(*step.preserve_components, "missing_component"),
    )
    assert TrajectoryViolationCode.MISSING_PRESERVED_REPRESENTATION in violation_codes(mutated)


def test_forbidden_representation_feature_is_rejected() -> None:
    mutated = replace_step(
        load_trajectory(),
        "position_probe6",
        forbidden_components=("numbers_row",),
    )
    assert TrajectoryViolationCode.FORBIDDEN_REPRESENTATION_PRESENT in violation_codes(mutated)


def test_forbidden_concept_disclosure_is_rejected() -> None:
    mutated = replace_step(
        load_trajectory(),
        "position_probe6",
        disclosed_concepts=("position_p", "index_i"),
    )
    assert TrajectoryViolationCode.FORBIDDEN_CONCEPT_DISCLOSED in violation_codes(mutated)


def test_answer_leak_in_probe_text_is_rejected() -> None:
    trajectory = load_trajectory()
    step = next(step for step in trajectory.steps if step.step_id == "position_probe6")
    assert step.probe is not None
    probe = step.probe.model_copy(update={"prompt": step.probe.prompt + " p = 4"})
    mutated = replace_step(trajectory, step.step_id, probe=probe)
    assert TrajectoryViolationCode.ANSWER_LITERAL_LEAKED in violation_codes(mutated)


def test_answer_leak_in_visible_representation_is_rejected() -> None:
    trajectory = load_trajectory()
    representation = next(
        representation
        for representation in trajectory.representations
        if representation.representation_id == "r.position_probe6"
    )
    mutated = replace_representation(
        trajectory,
        representation.representation_id,
        annotations=(*representation.annotations, "p = 4"),
    )
    assert TrajectoryViolationCode.ANSWER_LITERAL_LEAKED in violation_codes(mutated)


def test_answer_literals_are_not_policed_when_reveal_is_allowed() -> None:
    trajectory = load_trajectory()
    step = next(step for step in trajectory.steps if step.step_id == "position_probe6")
    assert step.probe is not None
    probe = step.probe.model_copy(
        update={"prompt": step.probe.prompt + " p = 4", "answer_reveal_allowed": True}
    )
    mutated = replace_step(trajectory, step.step_id, probe=probe)
    assert TrajectoryViolationCode.ANSWER_LITERAL_LEAKED not in violation_codes(mutated)


def test_empty_forbidden_answer_literal_is_ignored() -> None:
    trajectory = load_trajectory()
    step = next(step for step in trajectory.steps if step.step_id == "position_probe6")
    assert step.probe is not None
    probe = step.probe.model_copy(update={"forbidden_answer_literals": ("",)})
    mutated = replace_step(trajectory, step.step_id, probe=probe)
    assert TrajectoryViolationCode.ANSWER_LITERAL_LEAKED not in violation_codes(mutated)


def test_probe_without_probe_contract_is_rejected() -> None:
    mutated = replace_step(load_trajectory(), "position_probe6", probe=None)
    assert TrajectoryViolationCode.MISSING_PROBE_CONTRACT in violation_codes(mutated)


def test_non_probe_with_probe_contract_is_rejected() -> None:
    trajectory = load_trajectory()
    probe = next(step.probe for step in trajectory.steps if step.step_id == "position_probe6")
    mutated = replace_step(trajectory, "problem_anchor", probe=probe)
    assert TrajectoryViolationCode.UNEXPECTED_PROBE_CONTRACT in violation_codes(mutated)


def test_invalid_automatic_route_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.automatic_transitions[0].model_copy(
        update={"next_step_id": None, "exit_target": None}
    )
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (first, *trajectory.automatic_transitions[1:])}
    )
    assert TrajectoryViolationCode.INVALID_AUTO_ROUTE in violation_codes(mutated)


def test_unknown_automatic_source_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.automatic_transitions[0].model_copy(update={"from_step_id": "missing"})
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (first, *trajectory.automatic_transitions[1:])}
    )
    assert TrajectoryViolationCode.UNKNOWN_AUTO_SOURCE in violation_codes(mutated)


def test_unknown_automatic_target_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.automatic_transitions[0].model_copy(update={"next_step_id": "missing"})
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (first, *trajectory.automatic_transitions[1:])}
    )
    assert TrajectoryViolationCode.UNKNOWN_AUTO_TARGET in violation_codes(mutated)


def test_invalid_outcome_route_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.outcome_routes[0].model_copy(
        update={"next_step_id": None, "exit_target": None}
    )
    mutated = trajectory.model_copy(update={"outcome_routes": (first, *trajectory.outcome_routes[1:])})
    assert TrajectoryViolationCode.INVALID_OUTCOME_ROUTE in violation_codes(mutated)


def test_unknown_outcome_source_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.outcome_routes[0].model_copy(update={"after_step_id": "missing"})
    mutated = trajectory.model_copy(update={"outcome_routes": (first, *trajectory.outcome_routes[1:])})
    assert TrajectoryViolationCode.UNKNOWN_OUTCOME_SOURCE in violation_codes(mutated)


def test_unknown_outcome_target_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.outcome_routes[0].model_copy(update={"next_step_id": "missing"})
    mutated = trajectory.model_copy(update={"outcome_routes": (first, *trajectory.outcome_routes[1:])})
    assert TrajectoryViolationCode.UNKNOWN_OUTCOME_TARGET in violation_codes(mutated)


def test_probe_with_automatic_and_outcome_control_is_rejected_as_ambiguous() -> None:
    trajectory = load_trajectory()
    extra = AutomaticTransition(
        transition_id="auto.illegal-probe-control",
        from_step_id="position_probe6",
        next_step_id="position_validate6_correct",
        exit_target=None,
        evidence_turn_refs=("synthetic",),
    )
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (*trajectory.automatic_transitions, extra)}
    )
    assert TrajectoryViolationCode.AMBIGUOUS_STEP_CONTROL in violation_codes(mutated)


def test_non_probe_without_exactly_one_automatic_transition_is_rejected() -> None:
    trajectory = load_trajectory()
    autos = tuple(
        transition
        for transition in trajectory.automatic_transitions
        if transition.from_step_id != "problem_anchor"
    )
    mutated = trajectory.model_copy(update={"automatic_transitions": autos})
    assert TrajectoryViolationCode.AMBIGUOUS_STEP_CONTROL in violation_codes(mutated)


def test_duplicate_outcome_kind_for_same_probe_is_rejected() -> None:
    trajectory = load_trajectory()
    original = next(
        route
        for route in trajectory.outcome_routes
        if route.after_step_id == "position_probe6" and route.outcome == TrajectoryOutcomeKind.CORRECT
    )
    duplicate = original.model_copy(update={"route_id": "route.position6.correct.duplicate"})
    mutated = trajectory.model_copy(update={"outcome_routes": (*trajectory.outcome_routes, duplicate)})
    assert TrajectoryViolationCode.DUPLICATE_OUTCOME_KIND in violation_codes(mutated)


def test_skipped_state_becomes_unreachable() -> None:
    trajectory = load_trajectory()
    first = trajectory.automatic_transitions[0].model_copy(update={"next_step_id": "position_probe6"})
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (first, *trajectory.automatic_transitions[1:])}
    )
    codes = violation_codes(mutated)
    assert TrajectoryViolationCode.UNREACHABLE_STEP in codes


def test_cycle_is_rejected() -> None:
    trajectory = load_trajectory()
    last = trajectory.automatic_transitions[-1].model_copy(
        update={"next_step_id": "problem_anchor", "exit_target": None}
    )
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (*trajectory.automatic_transitions[:-1], last)}
    )
    assert TrajectoryViolationCode.CYCLE_DETECTED in violation_codes(mutated)


def test_outcome_route_with_both_targets_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.outcome_routes[0].model_copy(update={"exit_target": "also-exit"})
    mutated = trajectory.model_copy(update={"outcome_routes": (first, *trajectory.outcome_routes[1:])})
    assert TrajectoryViolationCode.INVALID_OUTCOME_ROUTE in violation_codes(mutated)


def test_automatic_route_with_both_targets_is_rejected() -> None:
    trajectory = load_trajectory()
    first = trajectory.automatic_transitions[0].model_copy(update={"exit_target": "also-exit"})
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (first, *trajectory.automatic_transitions[1:])}
    )
    assert TrajectoryViolationCode.INVALID_AUTO_ROUTE in violation_codes(mutated)


def test_non_probe_kind_still_requires_automatic_control() -> None:
    trajectory = load_trajectory()
    mutated = replace_step(trajectory, "position_validate7", kind=VerticalStepKind.BRIDGE)
    assert TrajectoryViolationCode.AMBIGUOUS_STEP_CONTROL not in violation_codes(mutated)
