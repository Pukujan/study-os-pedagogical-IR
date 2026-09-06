# Local Codex compiler smoke test

This is the first local model-backed compiler path for PIR-1. It uses the installed Codex CLI as transport. The model proposes a learner-independent `CanonicalProblemPIR`; Study OS validates and records it deterministically.

## 1. Verify without spending a model call

If Luna is exposed as a Codex profile:

```bash
python tools/compile_problem.py \
  --input fixtures/public/compiler-development/binary-search.input.v0.json \
  --policy fixtures/public/compiler-policies/compiler-p4.0.1.0.json \
  --output-dir runs/local/binary-search-p4 \
  --profile luna \
  --dry-run
```

If Luna is exposed as a model name instead, replace `--profile luna` with `--model <exact-model-name>`.

The dry run prints the exact headless `codex exec` command and compiler prompt. It does not invoke the model.

## 2. Run the compiler

Remove `--dry-run`:

```bash
python tools/compile_problem.py \
  --input fixtures/public/compiler-development/binary-search.input.v0.json \
  --policy fixtures/public/compiler-policies/compiler-p4.0.1.0.json \
  --output-dir runs/local/binary-search-p4 \
  --profile luna
```

The adapter invokes Codex with an ephemeral session, an isolated temporary working directory, a read-only sandbox, and the Pydantic JSON schema for `CanonicalProblemPIR` as the output schema.

## 3. Inspect artifacts

The output directory contains:

- `prompt.txt` — exact compiler prompt;
- `codex.command.json` — exact Codex invocation;
- `candidate.raw` — exact final model bytes, including malformed output;
- `candidate.json` — normalized parsed PIR when schema-valid;
- `projection.json` — narrow graph projection for the independent benchmarker;
- `receipt.json` — model/prompt/input identities, hashes, parse state, and deterministic PIR violations;
- `codex.stderr.txt` — Codex diagnostics.

Exit codes:

- `0` — schema-valid candidate accepted by deterministic PIR validation;
- `1` — model returned a candidate but it was malformed or rejected;
- `2` — Codex execution failed or produced no candidate.

A successful local development run is not hidden-generalization evidence. User Codex configuration is still allowed in this smoke-test path so a locally configured Luna provider/profile remains available. Sealed evaluation requires a separately isolated candidate environment and contamination receipt.
