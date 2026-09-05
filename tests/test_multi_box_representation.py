from __future__ import annotations

from study_os_pir.vertical import (
    ExperimentalVerticalSlice,
    VerticalRepresentation,
    VerticalRow,
    VerticalStep,
    VerticalStepKind,
    VerticalWindowBox,
    render_vertical_slice,
    validate_vertical_slice,
)


def test_multi_box_representation_is_structured_and_renderable() -> None:
    representation = VerticalRepresentation(
        representation_id="two-boxes",
        rows=(
            VerticalRow(
                row_id="numbers",
                label="numbers(a)",
                values=("3", "8", "1", "5", "2", "7"),
            ),
        ),
        boxes=(
            VerticalWindowBox(start_index=0, width=3, label="sum[i]"),
            VerticalWindowBox(start_index=1, width=3, label="sum[i+1]"),
        ),
        visible_components=("numbers_row", "box_comparison"),
    )
    slice_ = ExperimentalVerticalSlice(
        schema_version="pir.experimental-vertical-slice.v0",
        slice_id="multi-box",
        source_locator="source",
        representations=(representation,),
        steps=(
            VerticalStep(
                step_id="compare",
                kind=VerticalStepKind.COMPARE,
                goal="Compare the same box before and after one move.",
                representation_id="two-boxes",
                preserve_components=("numbers_row", "window_box", "box_comparison"),
                active_delta="add only the next box",
                evidence_note="source-backed comparison",
            ),
        ),
    )

    assert validate_vertical_slice(slice_) == ()
    rendered = render_vertical_slice(slice_)
    assert "sum[i]" in rendered
    assert "sum[i+1]" in rendered
    assert rendered.count("^^^") == 6
