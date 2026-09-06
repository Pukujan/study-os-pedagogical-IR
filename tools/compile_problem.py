from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import uuid
from pathlib import Path

from study_os_pir.compiler import CanonicalProblemPIR, CompilerPolicy, ProblemCompilerInput
from study_os_pir.compiler_artifacts import (
    build_decomposition_projection,
    parse_compiler_candidate,
    render_compiler_prompt,
)
from study_os_pir.compiler_runs import (
    CandidateParseStatus,
    GenerationSetting,
    build_compiler_run_receipt,
)

ROOT = Path(__file__).resolve().parents[1]


def _git_revision() -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _codex_version(binary: str) -> str:
    try:
        completed = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "unavailable"
    if completed.returncode != 0:
        return "unavailable"
    return completed.stdout.strip() or "unavailable"


def _codex_command(
    *,
    binary: str,
    workspace: Path,
    schema_path: Path,
    final_path: Path,
    model: str | None,
    profile: str | None,
) -> list[str]:
    command = [
        binary,
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--color",
        "never",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(final_path),
        "--cd",
        str(workspace),
    ]
    if profile:
        command.extend(("--profile", profile))
    if model:
        command.extend(("--model", model))
    command.append("-")
    return command


def _model_id(model: str | None, profile: str | None, explicit: str | None) -> str:
    if explicit:
        return explicit
    if model:
        return model
    if profile:
        return f"codex-profile:{profile}"
    return "codex-cli-default-unverified"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile one canonical Problem PIR through a local Codex CLI model."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--codex-binary", default="codex")
    parser.add_argument("--model")
    parser.add_argument("--profile")
    parser.add_argument("--model-id")
    parser.add_argument("--model-revision", default="unreported-by-codex-cli")
    parser.add_argument("--pir-revision")
    parser.add_argument("--benchmarker-revision", default="not-evaluated")
    parser.add_argument("--run-id")
    parser.add_argument("--attempt-index", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    compiler_input = ProblemCompilerInput.model_validate_json(args.input.read_text())
    policy = CompilerPolicy.model_validate_json(args.policy.read_text())
    prompt = render_compiler_prompt(compiler_input, policy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "prompt.txt").write_text(prompt)

    with tempfile.TemporaryDirectory(prefix="study-os-compiler-") as tmp:
        workspace = Path(tmp)
        schema_path = workspace / "canonical-problem-pir.schema.json"
        final_path = workspace / "candidate.final.json"
        schema_path.write_text(
            json.dumps(CanonicalProblemPIR.model_json_schema(), indent=2, sort_keys=True)
        )
        command = _codex_command(
            binary=args.codex_binary,
            workspace=workspace,
            schema_path=schema_path,
            final_path=final_path,
            model=args.model,
            profile=args.profile,
        )
        (args.output_dir / "codex.command.json").write_text(json.dumps(command, indent=2))

        if args.dry_run:
            print("Codex command:")
            print(" ".join(command))
            print("\nCompiler prompt:\n")
            print(prompt)
            return 0

        execution_error = ""
        return_code = 0
        stdout = ""
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                check=False,
                timeout=args.timeout,
            )
            return_code = completed.returncode
            stdout = completed.stdout
            execution_error = completed.stderr
        except FileNotFoundError:
            return_code = 127
            execution_error = f"Codex binary not found: {args.codex_binary}"
        except subprocess.TimeoutExpired:
            return_code = 124
            execution_error = f"Codex execution exceeded {args.timeout} seconds"

        candidate_bytes = final_path.read_bytes() if final_path.exists() else stdout.encode()
        if return_code != 0 or not candidate_bytes:
            parse_status = CandidateParseStatus.EXECUTION_FAILED
            proposal = None
        else:
            parse_status, proposal = parse_compiler_candidate(candidate_bytes)

    (args.output_dir / "candidate.raw").write_bytes(candidate_bytes)
    (args.output_dir / "codex.stderr.txt").write_text(execution_error)

    model_id = _model_id(args.model, args.profile, args.model_id)
    codex_version = _codex_version(args.codex_binary)
    settings = [
        GenerationSetting(name="adapter", value="codex-cli"),
        GenerationSetting(name="codex_cli_version", value=codex_version),
        GenerationSetting(name="sandbox", value="read-only"),
        GenerationSetting(name="ephemeral", value="true"),
    ]
    if args.profile:
        settings.append(GenerationSetting(name="profile", value=args.profile))
    if args.model:
        settings.append(GenerationSetting(name="model_flag", value=args.model))

    receipt = build_compiler_run_receipt(
        run_id=args.run_id or str(uuid.uuid4()),
        attempt_index=args.attempt_index,
        compiler_input=compiler_input,
        policy=policy,
        candidate_bytes=candidate_bytes,
        parse_status=parse_status,
        proposal=proposal,
        model_id=model_id,
        model_revision=args.model_revision,
        pir_revision=args.pir_revision or _git_revision(),
        benchmarker_revision=args.benchmarker_revision,
        generation_settings=tuple(settings),
    )
    (args.output_dir / "receipt.json").write_text(receipt.model_dump_json(indent=2))

    if proposal is not None:
        (args.output_dir / "candidate.json").write_text(proposal.model_dump_json(indent=2))
        projection = build_decomposition_projection(
            proposal,
            candidate_id=model_id,
            candidate_version=args.model_revision,
        )
        (args.output_dir / "projection.json").write_text(
            json.dumps(projection, indent=2, sort_keys=True)
        )

    print(f"parse_status={receipt.parse_status.value}")
    print(f"accepted={str(receipt.accepted).lower()}")
    if receipt.compiler_violation_codes:
        print(
            "compiler_violations="
            + ",".join(code.value for code in receipt.compiler_violation_codes)
        )
    print(f"artifacts={args.output_dir}")

    if parse_status == CandidateParseStatus.EXECUTION_FAILED:
        return 2
    return 0 if receipt.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
