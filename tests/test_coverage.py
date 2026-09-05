from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from study_os_pir import (
    ExtractionLedger,
    PrimaryDisposition,
    TurnDisposition,
    assert_extraction_complete,
    evaluate_extraction_coverage,
)


def disposition(
    turn_id: str,
    *,
    disposition_id: str | None = None,
    revision: str = "r1",
    primary: PrimaryDisposition = PrimaryDisposition.META,
) -> TurnDisposition:
    return TurnDisposition(
        schema_version="pir.turn-disposition.v1",
        disposition_id=disposition_id or f"d-{turn_id}",
        extraction_revision=revision,
        turn_id=turn_id,
        primary_disposition=primary,
    )


def ledger(*items: TurnDisposition, revision: str = "r1") -> ExtractionLedger:
    return ExtractionLedger(
        schema_version="pir.extraction-ledger.v1",
        ledger_id="ledger-1",
        extraction_revision=revision,
        dispositions=items,
    )


def test_exact_authoritative_set_is_complete() -> None:
    current = ledger(
        disposition("t1", primary=PrimaryDisposition.GOLDEN),
        disposition("t2", primary=PrimaryDisposition.EXERCISE),
    )

    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1", "t2"),
        ledger=current,
    )

    assert report.complete is True
    assert report.expected_source_turn_count == 2
    assert report.disposition_record_count == 2
    assert report.unique_disposed_source_turn_count == 2
    assert report.missing_turn_ids == ()
    assert assert_extraction_complete(
        authoritative_turn_ids=("t1", "t2"), ledger=current
    ) == report


def test_empty_authoritative_source_and_empty_ledger_is_complete() -> None:
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=(),
        ledger=ledger(),
    )
    assert report.complete is True
    assert report.expected_source_turn_count == 0
    assert report.unique_disposed_source_turn_count == 0


def test_missing_source_turn_is_reported_and_completion_fails_closed() -> None:
    current = ledger(disposition("t1"))
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1", "t2"),
        ledger=current,
    )

    assert report.complete is False
    assert report.missing_turn_ids == ("t2",)
    with pytest.raises(ValueError, match="extraction coverage incomplete"):
        assert_extraction_complete(
            authoritative_turn_ids=("t1", "t2"),
            ledger=current,
        )


def test_duplicate_primary_disposition_for_turn_is_rejected() -> None:
    current = ledger(
        disposition("t1", disposition_id="d1"),
        disposition("t1", disposition_id="d2"),
    )
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1",),
        ledger=current,
    )

    assert report.complete is False
    assert report.duplicate_turn_ids == ("t1",)


def test_unknown_turn_cannot_make_ledger_complete() -> None:
    current = ledger(disposition("t1"), disposition("ghost"))
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1",),
        ledger=current,
    )

    assert report.complete is False
    assert report.unknown_turn_ids == ("ghost",)
    assert report.unique_disposed_source_turn_count == 1


def test_duplicate_disposition_id_is_rejected_even_across_different_turns() -> None:
    current = ledger(
        disposition("t1", disposition_id="same"),
        disposition("t2", disposition_id="same"),
    )
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1", "t2"),
        ledger=current,
    )

    assert report.complete is False
    assert report.duplicate_disposition_ids == ("same",)


def test_revision_mismatch_does_not_satisfy_source_turn_coverage() -> None:
    current = ledger(disposition("t1", disposition_id="old", revision="r0"))
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1",),
        ledger=current,
    )

    assert report.complete is False
    assert report.revision_mismatched_disposition_ids == ("old",)
    assert report.missing_turn_ids == ("t1",)
    assert report.unique_disposed_source_turn_count == 0


def test_duplicate_authoritative_turn_ids_fail_closed() -> None:
    current = ledger(disposition("t1"))
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1", "t1"),
        ledger=current,
    )

    assert report.complete is False
    assert report.duplicate_authoritative_turn_ids == ("t1",)
    assert report.expected_source_turn_count == 2


@given(st.permutations(("t1", "t2", "t3")))
def test_authoritative_input_order_does_not_change_coverage(permutation: list[str]) -> None:
    current = ledger(disposition("t1"), disposition("t2"), disposition("t3"))
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=tuple(permutation),
        ledger=current,
    )
    assert report.complete is True


@given(st.permutations((0, 1, 2)))
def test_disposition_record_order_does_not_change_coverage(permutation: list[int]) -> None:
    items = (disposition("t1"), disposition("t2"), disposition("t3"))
    current = ledger(*(items[index] for index in permutation))
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1", "t2", "t3"),
        ledger=current,
    )
    assert report.complete is True
