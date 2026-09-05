# Canonicalization — PIR v0.1

## Purpose

Canonicalization exists so identical validated IR produces identical bytes and digests across runs and machines.

It does **not** normalize source evidence. Source evidence is hashed as original bytes.

## Source evidence

For `EvidenceArtifact`:

```text
artifact_digest = sha256(original_bytes)
```

No decoding, newline conversion, Unicode normalization, BOM removal, trimming or re-encoding occurs before this digest.

## Canonical JSON for derived/IR objects

v0.1 canonical JSON rules:

1. UTF-8 encoding.
2. JSON object keys sorted lexicographically by Unicode code point as implemented by the pinned canonicalizer.
3. Separators are `,` and `:` with no insignificant whitespace.
4. Unicode is emitted directly (`ensure_ascii = false` behavior), then encoded as UTF-8.
5. Arrays preserve declared semantic order.
6. Set-like semantics are represented as arrays sorted by an object-specific rule before canonical serialization.
7. `null` fields are included only when the schema declares `null` semantically distinct from absence. Otherwise optional absent fields stay absent.
8. Floating-point numbers are prohibited from semantic v0.1 objects unless a future version specifies exact number canonicalization.
9. NaN/Infinity are prohibited.
10. Runtime timestamps, filesystem paths, database IDs, random UUIDs and process metadata are excluded from semantic digests unless explicitly declared semantic by a future schema.

## Digests

```text
semantic_digest = sha256(canonical_json_bytes(validated_object))
```

Digests are integrity/reproducibility identifiers, not proof of pedagogical correctness.

## Ordered vs set-like fields

Examples of ordered fields:

- source span sequence when concatenation order matters;
- context turn order;
- trajectory required path;
- correction/retry/verify sequence.

Examples of set-like fields:

- forbidden concept identifiers;
- immutable representation component identifiers;
- required-preserve identifiers when order has no meaning.

Each schema/validator must explicitly define whether an array is ordered or set-like. Never infer this from implementation container type.

## Stable IDs

v0.1 allows human/caller-provided stable IDs. A stable ID is not automatically recomputed from content because identity and content revision can differ.

Every revision-sensitive object should additionally support a semantic digest so mutation is detectable.

## Compatibility

Changing canonicalization semantics is a breaking change. Introduce a new canonicalization version and do not recompute historical digests under new rules while presenting them as original.

## Required tests

- identical object, repeated serialization → byte-identical;
- dictionary construction order changes → identical canonical bytes;
- ordered array permutation → different digest where order is semantic;
- set-like input permutation → identical canonical bytes after semantic normalization;
- Unicode content round trip;
- source CRLF/LF difference → different source artifact digest;
- trailing byte change → different source artifact digest;
- volatile metadata excluded from semantic digest where specified.
