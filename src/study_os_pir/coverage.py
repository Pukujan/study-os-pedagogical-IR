from __future__ import annotations

from collections import Counter

from .models import CoverageReport, ExtractionLedger


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    counts = Counter(values)
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def evaluate_extraction_coverage(
    *,
    authoritative_turn_ids: tuple[str, ...],
    ledger: ExtractionLedger,
) -> CoverageReport:
    duplicate_authoritative_turn_ids = _duplicates(authoritative_turn_ids)
    expected_turn_ids = set(authoritative_turn_ids)

    all_disposition_turn_ids = tuple(item.turn_id for item in ledger.dispositions)
    duplicate_turn_ids = _duplicates(all_disposition_turn_ids)
    duplicate_disposition_ids = _duplicates(
        tuple(item.disposition_id for item in ledger.dispositions)
    )

    revision_mismatched_disposition_ids = tuple(
        sorted(
            item.disposition_id
            for item in ledger.dispositions
            if item.extraction_revision != ledger.extraction_revision
        )
    )
    matching_revision = tuple(
        item
        for item in ledger.dispositions
        if item.extraction_revision == ledger.extraction_revision
    )
    matching_turn_ids = {item.turn_id for item in matching_revision}

    missing_turn_ids = tuple(sorted(expected_turn_ids - matching_turn_ids))
    unknown_turn_ids = tuple(sorted(set(all_disposition_turn_ids) - expected_turn_ids))
    unique_disposed_source_turn_count = len(expected_turn_ids & matching_turn_ids)

    complete = not any(
        (
            duplicate_authoritative_turn_ids,
            missing_turn_ids,
            duplicate_turn_ids,
            unknown_turn_ids,
            duplicate_disposition_ids,
            revision_mismatched_disposition_ids,
        )
    )

    return CoverageReport(
        schema_version="pir.coverage-report.v1",
        ledger_id=ledger.ledger_id,
        extraction_revision=ledger.extraction_revision,
        expected_source_turn_count=len(authoritative_turn_ids),
        disposition_record_count=len(ledger.dispositions),
        unique_disposed_source_turn_count=unique_disposed_source_turn_count,
        missing_turn_ids=missing_turn_ids,
        duplicate_turn_ids=duplicate_turn_ids,
        unknown_turn_ids=unknown_turn_ids,
        duplicate_disposition_ids=duplicate_disposition_ids,
        revision_mismatched_disposition_ids=revision_mismatched_disposition_ids,
        duplicate_authoritative_turn_ids=duplicate_authoritative_turn_ids,
        complete=complete,
    )


def assert_extraction_complete(
    *,
    authoritative_turn_ids: tuple[str, ...],
    ledger: ExtractionLedger,
) -> CoverageReport:
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=authoritative_turn_ids,
        ledger=ledger,
    )
    if not report.complete:
        raise ValueError(
            "extraction coverage incomplete: "
            f"missing={report.missing_turn_ids}, "
            f"duplicate_turns={report.duplicate_turn_ids}, "
            f"unknown={report.unknown_turn_ids}, "
            f"duplicate_dispositions={report.duplicate_disposition_ids}, "
            f"revision_mismatch={report.revision_mismatched_disposition_ids}, "
            f"duplicate_source={report.duplicate_authoritative_turn_ids}"
        )
    return report
