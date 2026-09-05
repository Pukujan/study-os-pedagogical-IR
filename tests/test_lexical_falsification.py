from __future__ import annotations

from pathlib import Path

from study_os_pir.trajectory import ExperimentalTrajectory, validate_trajectory

ROOT = Path(__file__).resolve().parents[1]
TRAJECTORY_PATH = (
    ROOT
    / "fixtures"
    / "public"
    / "sliding-window-foundations"
    / "trajectory.i-sum.v0.json"
)


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(TRAJECTORY_PATH.read_text())


def test_current_pir_does_not_detect_premature_technical_vocabulary_drift() -> None:
    trajectory = load_trajectory()
    target = next(
        representation
        for representation in trajectory.representations
        if representation.representation_id == "r.i_intro0"
    )
    rows = tuple(
        row.model_copy(update={"label": "elements(a)"})
        if row.row_id == "numbers_row"
        else row
        for row in target.rows
    )
    annotations = tuple(
        annotation.replace("box", "window") for annotation in target.annotations
    )
    mutated_representation = target.model_copy(
        update={"rows": rows, "annotations": annotations}
    )
    representations = tuple(
        mutated_representation
        if representation.representation_id == target.representation_id
        else representation
        for representation in trajectory.representations
    )
    mutated = trajectory.model_copy(update={"representations": representations})

    # Falsification result: semantics, concept IDs, representation features, and
    # control flow remain valid even though learner-facing register changed from
    # grounded "numbers/box" language to premature "elements/window" language.
    assert validate_trajectory(mutated) == ()
