from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .models import StrictFrozenModel
from .vertical import VerticalProbe, VerticalRepresentation, VerticalStepKind


class TrajectoryOutcomeKind(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"
    META = "meta"


class TrajectoryViolationCode(StrEnum):
    DUPLICATE_STEP_ID = "DUPLICATE_STEP_ID"
    DUPLICATE_REPRESENTATION_ID = "DUPLICATE_REPRESENTATION_ID"
    DUPLICATE_AUTO_TRANSITION_ID = "DUPLICATE_AUTO_TRANSITION_ID"
    DUPLICATE_OUTCOME_ROUTE_ID = "DUPLICATE_OUTCOME_ROUTE_ID"
    UNKNOWN_ENTRY_STEP = "UNKNOWN_ENTRY_STEP"
    UNKNOWN_REPRESENTATION = "UNKNOWN_REPRESENTATION"
    MISSING_PRESERVED_REPRESENTATION = "MISSING_PRESERVED_REPRESENTATION"
    FORBIDDEN_REPRESENTATION_PRESENT = "FORBIDDEN_REPRESENTATION_PRESENT"
    FORBIDDEN_CONCEPT_DISCLOSED = "FORBIDDEN_CONCEPT_DISCLOSED"
    ANSWER_LITERAL_LEAKED = "ANSWER_LITERAL_LEAKED"
    MISSING_PROBE_CONTRACT = "MISSING_PROBE_CONTRACT"
    UNEXPECTED_PROBE_CONTRACT = "UNEXPECTED_PROBE_CONTRACT"
    INVALID_AUTO_ROUTE = "INVALID_AUTO_ROUTE"
    INVALID_OUTCOME_ROUTE = "INVALID_OUTCOME_ROUTE"
    UNKNOWN_AUTO_SOURCE = "UNKNOWN_AUTO_SOURCE"
    UNKNOWN_AUTO_TARGET = "UNKNOWN_AUTO_TARGET"
    UNKNOWN_OUTCOME_SOURCE = "UNKNOWN_OUTCOME_SOURCE"
    UNKNOWN_OUTCOME_TARGET = "UNKNOWN_OUTCOME_TARGET"
    AMBIGUOUS_STEP_CONTROL = "AMBIGUOUS_STEP_CONTROL"
    DUPLICATE_OUTCOME_KIND = "DUPLICATE_OUTCOME_KIND"
    UNREACHABLE_STEP = "UNREACHABLE_STEP"
    CYCLE_DETECTED = "CYCLE_DETECTED"


class TrajectoryStep(StrictFrozenModel):
    step_id: str = Field(min_length=1)
    kind: VerticalStepKind
    goal: str = Field(min_length=1)
    representation_id: str = Field(min_length=1)
    preserve_components: tuple[str, ...] = ()
    forbidden_components: tuple[str, ...] = ()
    active_delta: str = Field(min_length=1)
    disclosed_concepts: tuple[str, ...] = ()
    forbidden_concepts: tuple[str, ...] = ()
    probe: VerticalProbe | None = None
    evidence_turn_refs: tuple[str, ...] = Field(min_length=1)


class AutomaticTransition(StrictFrozenModel):
    transition_id: str = Field(min_length=1)
    from_step_id: str = Field(min_length=1)
    next_step_id: str | None = Field(default=None, min_length=1)
    exit_target: str | None = Field(default=None, min_length=1)
    evidence_turn_refs: tuple[str, ...] = Field(min_length=1)


class OutcomeRoute(StrictFrozenModel):
    route_id: str = Field(min_length=1)
    after_step_id: str = Field(min_length=1)
    outcome: TrajectoryOutcomeKind
    next_step_id: str | None = Field(default=None, min_length=1)
    exit_target: str | None = Field(default=None, min_length=1)
    evidence_turn_refs: tuple[str, ...] = Field(min_length=1)


class ExperimentalTrajectory(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.experimental-trajectory\.v0$")
    trajectory_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    entry_step_id: str = Field(min_length=1)
    representations: tuple[VerticalRepresentation, ...] = Field(min_length=1)
    steps: tuple[TrajectoryStep, ...] = Field(min_length=1)
    automatic_transitions: tuple[AutomaticTransition, ...] = ()
    outcome_routes: tuple[OutcomeRoute, ...] = ()


class TrajectoryViolation(StrictFrozenModel):
    code: TrajectoryViolationCode
    detail: str = Field(min_length=1)


class TrajectorySimulation(StrictFrozenModel):
    visited_step_ids: tuple[str, ...]
    consumed_outcomes: tuple[TrajectoryOutcomeKind, ...]
    awaiting_step_id: str | None = None
    exit_target: str | None = None


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def _exclusive_route(next_step_id: str | None, exit_target: str | None) -> bool:
    return (next_step_id is None) != (exit_target is None)


def _representation_features(representation: VerticalRepresentation) -> set[str]:
    features = set(representation.visible_components)
    if representation.box is not None:
        features.add("window_box")
    return features


def _representation_surface(representation: VerticalRepresentation) -> str:
    values: list[str] = []
    for row in representation.rows:
        values.append(row.label)
        values.extend(row.values)
    values.extend(representation.annotations)
    return "\n".join(values)


def _target_step_ids(trajectory: ExperimentalTrajectory) -> dict[str, tuple[str, ...]]:
    targets: dict[str, list[str]] = {step.step_id: [] for step in trajectory.steps}
    for transition in trajectory.automatic_transitions:
        if transition.from_step_id in targets and transition.next_step_id is not None:
            targets[transition.from_step_id].append(transition.next_step_id)
    for route in trajectory.outcome_routes:
        if route.after_step_id in targets and route.next_step_id is not None:
            targets[route.after_step_id].append(route.next_step_id)
    return {step_id: tuple(step_targets) for step_id, step_targets in targets.items()}


def _reachable_step_ids(trajectory: ExperimentalTrajectory) -> set[str]:
    adjacency = _target_step_ids(trajectory)
    if trajectory.entry_step_id not in adjacency:
        return set()
    reachable: set[str] = set()
    stack = [trajectory.entry_step_id]
    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        reachable.add(current)
        stack.extend(target for target in adjacency[current] if target in adjacency)
    return reachable


def _has_cycle(trajectory: ExperimentalTrajectory) -> bool:
    adjacency = _target_step_ids(trajectory)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> bool:
        if step_id in visiting:
            return True
        if step_id in visited:
            return False
        visiting.add(step_id)
        for target in adjacency.get(step_id, ()):
            if target in adjacency and visit(target):
                return True
        visiting.remove(step_id)
        visited.add(step_id)
        return False

    return any(visit(step_id) for step_id in adjacency if step_id not in visited)


def validate_trajectory(trajectory: ExperimentalTrajectory) -> tuple[TrajectoryViolation, ...]:
    violations: list[TrajectoryViolation] = []
    step_ids = tuple(step.step_id for step in trajectory.steps)
    representation_ids = tuple(rep.representation_id for rep in trajectory.representations)
    transition_ids = tuple(item.transition_id for item in trajectory.automatic_transitions)
    route_ids = tuple(item.route_id for item in trajectory.outcome_routes)
    step_id_set = set(step_ids)
    representation_by_id = {rep.representation_id: rep for rep in trajectory.representations}

    duplicate_specs = (
        (step_ids, TrajectoryViolationCode.DUPLICATE_STEP_ID, "step"),
        (
            representation_ids,
            TrajectoryViolationCode.DUPLICATE_REPRESENTATION_ID,
            "representation",
        ),
        (
            transition_ids,
            TrajectoryViolationCode.DUPLICATE_AUTO_TRANSITION_ID,
            "automatic transition",
        ),
        (route_ids, TrajectoryViolationCode.DUPLICATE_OUTCOME_ROUTE_ID, "outcome route"),
    )
    for values, code, label in duplicate_specs:
        for duplicate in _duplicates(values):
            violations.append(
                TrajectoryViolation(code=code, detail=f"duplicate {label} id: {duplicate}")
            )

    if trajectory.entry_step_id not in step_id_set:
        violations.append(
            TrajectoryViolation(
                code=TrajectoryViolationCode.UNKNOWN_ENTRY_STEP,
                detail=f"unknown entry step: {trajectory.entry_step_id}",
            )
        )

    for step in trajectory.steps:
        representation = representation_by_id.get(step.representation_id)
        if representation is None:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.UNKNOWN_REPRESENTATION,
                    detail=(
                        f"{step.step_id} references unknown representation "
                        f"{step.representation_id}"
                    ),
                )
            )
            continue

        features = _representation_features(representation)
        missing = sorted(set(step.preserve_components) - features)
        if missing:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.MISSING_PRESERVED_REPRESENTATION,
                    detail=f"{step.step_id} missing preserved component(s): {', '.join(missing)}",
                )
            )
        forbidden_present = sorted(set(step.forbidden_components).intersection(features))
        if forbidden_present:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.FORBIDDEN_REPRESENTATION_PRESENT,
                    detail=(
                        f"{step.step_id} contains forbidden representation feature(s): "
                        f"{', '.join(forbidden_present)}"
                    ),
                )
            )
        disclosed_forbidden = sorted(
            set(step.disclosed_concepts).intersection(step.forbidden_concepts)
        )
        if disclosed_forbidden:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.FORBIDDEN_CONCEPT_DISCLOSED,
                    detail=(
                        f"{step.step_id} disclosed forbidden concept(s): "
                        f"{', '.join(disclosed_forbidden)}"
                    ),
                )
            )
        if step.kind == VerticalStepKind.PROBE and step.probe is None:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.MISSING_PROBE_CONTRACT,
                    detail=f"{step.step_id} is a probe without a probe contract",
                )
            )
        if step.kind != VerticalStepKind.PROBE and step.probe is not None:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.UNEXPECTED_PROBE_CONTRACT,
                    detail=f"{step.step_id} is not a probe but carries a probe contract",
                )
            )
        if step.probe is not None and not step.probe.answer_reveal_allowed:
            surface = step.probe.prompt + "\n" + _representation_surface(representation)
            leaked = sorted(
                literal
                for literal in step.probe.forbidden_answer_literals
                if literal and literal in surface
            )
            if leaked:
                violations.append(
                    TrajectoryViolation(
                        code=TrajectoryViolationCode.ANSWER_LITERAL_LEAKED,
                        detail=f"{step.step_id} leaked answer literal(s): {', '.join(leaked)}",
                    )
                )

    autos_by_source: dict[str, list[AutomaticTransition]] = {}
    for transition in trajectory.automatic_transitions:
        autos_by_source.setdefault(transition.from_step_id, []).append(transition)
        if transition.from_step_id not in step_id_set:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.UNKNOWN_AUTO_SOURCE,
                    detail=(
                        f"{transition.transition_id} has unknown source "
                        f"{transition.from_step_id}"
                    ),
                )
            )
        if not _exclusive_route(transition.next_step_id, transition.exit_target):
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.INVALID_AUTO_ROUTE,
                    detail=(
                        f"{transition.transition_id} must select exactly one next step "
                        "or exit target"
                    ),
                )
            )
        elif transition.next_step_id is not None and transition.next_step_id not in step_id_set:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.UNKNOWN_AUTO_TARGET,
                    detail=(
                        f"{transition.transition_id} targets unknown step "
                        f"{transition.next_step_id}"
                    ),
                )
            )

    routes_by_source: dict[str, list[OutcomeRoute]] = {}
    for route in trajectory.outcome_routes:
        routes_by_source.setdefault(route.after_step_id, []).append(route)
        if route.after_step_id not in step_id_set:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.UNKNOWN_OUTCOME_SOURCE,
                    detail=f"{route.route_id} has unknown source {route.after_step_id}",
                )
            )
        if not _exclusive_route(route.next_step_id, route.exit_target):
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.INVALID_OUTCOME_ROUTE,
                    detail=(
                        f"{route.route_id} must select exactly one next step or exit target"
                    ),
                )
            )
        elif route.next_step_id is not None and route.next_step_id not in step_id_set:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.UNKNOWN_OUTCOME_TARGET,
                    detail=f"{route.route_id} targets unknown step {route.next_step_id}",
                )
            )

    for step in trajectory.steps:
        autos = autos_by_source.get(step.step_id, [])
        routes = routes_by_source.get(step.step_id, [])
        if step.kind == VerticalStepKind.PROBE:
            valid_control = not autos and bool(routes)
        else:
            valid_control = len(autos) == 1 and not routes
        if not valid_control:
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.AMBIGUOUS_STEP_CONTROL,
                    detail=(
                        f"{step.step_id} has {len(autos)} automatic transition(s) and "
                        f"{len(routes)} outcome route(s)"
                    ),
                )
            )
        outcome_kinds = tuple(route.outcome.value for route in routes)
        for duplicate in _duplicates(outcome_kinds):
            violations.append(
                TrajectoryViolation(
                    code=TrajectoryViolationCode.DUPLICATE_OUTCOME_KIND,
                    detail=f"{step.step_id} has duplicate outcome route for {duplicate}",
                )
            )

    reachable = _reachable_step_ids(trajectory)
    for step_id in sorted(step_id_set - reachable):
        violations.append(
            TrajectoryViolation(
                code=TrajectoryViolationCode.UNREACHABLE_STEP,
                detail=f"unreachable step: {step_id}",
            )
        )
    if _has_cycle(trajectory):
        violations.append(
            TrajectoryViolation(
                code=TrajectoryViolationCode.CYCLE_DETECTED,
                detail="trajectory contains a cycle; experimental v0 requires an acyclic graph",
            )
        )

    return tuple(violations)


def simulate_trajectory(
    trajectory: ExperimentalTrajectory,
    outcomes: tuple[TrajectoryOutcomeKind, ...],
) -> TrajectorySimulation:
    violations = validate_trajectory(trajectory)
    if violations:
        raise ValueError("cannot simulate invalid trajectory")

    auto_by_source = {
        transition.from_step_id: transition for transition in trajectory.automatic_transitions
    }
    routes_by_source = {
        (route.after_step_id, route.outcome): route for route in trajectory.outcome_routes
    }
    step_by_id = {step.step_id: step for step in trajectory.steps}
    visited: list[str] = []
    consumed: list[TrajectoryOutcomeKind] = []
    outcome_index = 0
    current = trajectory.entry_step_id

    while True:
        step = step_by_id[current]
        visited.append(current)
        if step.kind == VerticalStepKind.PROBE:
            if outcome_index >= len(outcomes):
                return TrajectorySimulation(
                    visited_step_ids=tuple(visited),
                    consumed_outcomes=tuple(consumed),
                    awaiting_step_id=current,
                )
            outcome = outcomes[outcome_index]
            outcome_index += 1
            route = routes_by_source.get((current, outcome))
            if route is None:
                raise ValueError(f"no route for outcome {outcome.value} after {current}")
            consumed.append(outcome)
            if route.exit_target is not None:
                return TrajectorySimulation(
                    visited_step_ids=tuple(visited),
                    consumed_outcomes=tuple(consumed),
                    exit_target=route.exit_target,
                )
            assert route.next_step_id is not None
            current = route.next_step_id
            continue

        transition = auto_by_source[current]
        if transition.exit_target is not None:
            return TrajectorySimulation(
                visited_step_ids=tuple(visited),
                consumed_outcomes=tuple(consumed),
                exit_target=transition.exit_target,
            )
        assert transition.next_step_id is not None
        current = transition.next_step_id
