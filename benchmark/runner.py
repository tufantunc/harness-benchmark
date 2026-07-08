# benchmark/runner.py
"""Docker orchestration: spawn one container per (harness x exercise x rep)."""
from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .store import Store, RunResult
from .task_loader import Exercise


@dataclass
class RunOutcome:
    metrics: dict
    skipped: bool = False


def run_single(
    config: Config,
    harness: str,
    exercise: Exercise,
    repetition: int,
    run_id: str,
) -> RunOutcome:
    """Run one (harness x exercise x rep) in a Docker container."""
    store = Store(Path(config.docker.results_volume) / "store.db")
    store.init_schema()

    if config.run.skip_existing and store.exists(
        harness, config.model.name, exercise.language, exercise.name, repetition
    ):
        return RunOutcome(metrics={}, skipped=True)

    image = config.docker.image
    results_vol = str(Path(config.docker.results_volume).resolve())

    env = [
        "-e", f"MODEL_URL={config.model.url}",
        "-e", f"PROTOCOL={config.model.protocol}",
        "-e", f"MODEL_NAME={config.model.name}",
        "-e", f"{config.model.api_key_env}={config.model.api_key}",
        "-e", f"TASK_TIMEOUT={config.run.timeout_sec}",
    ]

    cmd = [
        "docker", "run", "--rm",
        *env,
        "-v", f"{results_vol}:/results",
        image,
        harness,
        exercise.relpath,
        str(repetition),
        "/results",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=config.run.timeout_sec + 120)

    if result.returncode != 0:
        metrics = {
            "harness": harness,
            "model": config.model.name,
            "language": exercise.language,
            "exercise": exercise.name,
            "repetition": repetition,
            "success": False,
            "test_exit_code": -1,
            "agent_exit_code": result.returncode,
            "timed_out": True,
            "tampered": False,
            "tokens_input": 0,
            "tokens_output": 0,
            "tokens_cached": 0,
            "cost_usd": 0.0,
            "tool_calls": 0,
            "llm_calls": 0,
            "duration_sec": config.run.timeout_sec,
            "diff_loc": 0,
        }
    else:
        try:
            metrics = json.loads(result.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            metrics = {
                "harness": harness, "model": config.model.name,
                "language": exercise.language, "exercise": exercise.name,
                "repetition": repetition, "success": False,
                "test_exit_code": -1, "agent_exit_code": 0,
                "timed_out": False, "tampered": False,
                "tokens_input": 0, "tokens_output": 0, "tokens_cached": 0,
                "cost_usd": 0.0, "tool_calls": 0, "llm_calls": 0,
                "duration_sec": 0.0, "diff_loc": 0,
            }

    run_result = RunResult(
        run_id=run_id,
        harness=harness,
        model=config.model.name,
        language=exercise.language,
        exercise=exercise.name,
        repetition=repetition,
        success=metrics.get("success", False),
        tokens_input=metrics.get("tokens_input", 0),
        tokens_output=metrics.get("tokens_output", 0),
        tokens_cached=metrics.get("tokens_cached", 0),
        cost_usd=metrics.get("cost_usd", 0.0),
        duration_sec=metrics.get("duration_sec", 0.0),
        tool_calls=metrics.get("tool_calls", 0),
        llm_calls=metrics.get("llm_calls", 0),
        diff_loc=metrics.get("diff_loc", 0),
        timed_out=metrics.get("timed_out", False),
        tampered=metrics.get("tampered", False),
        artifact_path=f"artifacts/{harness}/{exercise.language}/{exercise.name}/rep-{repetition}",
    )
    store.upsert(run_result)

    return RunOutcome(metrics=metrics)


def run_benchmark(config: Config, exercises: list[Exercise]) -> dict:
    """Run the full benchmark: all harnesses x all exercises x repetitions."""
    run_id = str(uuid.uuid4())[:8]
    total = len(config.harnesses) * len(exercises) * config.run.repetitions
    completed = 0
    skipped = 0
    failed = 0

    print(f"Starting benchmark run {run_id}")
    print(f"  Harnesses: {config.harnesses}")
    print(f"  Model: {config.model.name} ({config.model.url})")
    print(f"  Exercises: {len(exercises)}")
    print(f"  Repetitions: {config.run.repetitions}")
    print(f"  Total runs: {total}")
    print()

    for harness in config.harnesses:
        for exercise in exercises:
            for rep in range(1, config.run.repetitions + 1):
                completed += 1
                print(f"[{completed}/{total}] {harness}/{exercise.language}/{exercise.name} rep-{rep}", end=" ... ")

                outcome = run_single(config, harness, exercise, rep, run_id)

                if outcome.skipped:
                    print("SKIP (exists)")
                    skipped += 1
                elif outcome.metrics.get("success"):
                    print("PASS")
                else:
                    print("FAIL")
                    failed += 1

    print()
    print(f"Done: {completed - skipped} ran, {skipped} skipped, {failed} failed")
    return {"run_id": run_id, "total": total, "skipped": skipped, "failed": failed}
