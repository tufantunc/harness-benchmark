# benchmark/config.py
"""Configuration loading: benchmark.yaml <- .env <- CLI overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ModelConfig:
    url: str = ""
    protocol: str = "openai"
    name: str = ""
    api_key_env: str = "LLM_API_KEY"

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


@dataclass
class TaskConfig:
    source: str = "polyglot"
    languages: list[str] = field(default_factory=lambda: ["python", "javascript"])
    addendum: str = ""


@dataclass
class RunConfig:
    repetitions: int = 3
    timeout_sec: int = 600
    skip_existing: bool = True
    retry_failed: bool = False
    parallel: int = 1


@dataclass
class DockerConfig:
    image: str = "harness:latest"
    results_volume: str = "./results"


@dataclass
class ReportingConfig:
    output: list[str] = field(default_factory=lambda: ["sqlite", "html", "markdown"])
    pages_path: str = "docs"
    auto_commit: bool = True


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    task: TaskConfig = field(default_factory=TaskConfig)
    run: RunConfig = field(default_factory=RunConfig)
    harnesses: list[str] = field(default_factory=lambda: ["opencode", "pi"])
    docker: DockerConfig = field(default_factory=DockerConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    base_dir: Path = Path(".")


def load_config(
    config_path: Path = Path("benchmark.yaml"),
    cli_overrides: dict | None = None,
) -> Config:
    cli_overrides = cli_overrides or {}
    raw = yaml.safe_load(config_path.read_text()) or {}

    model = ModelConfig(**raw.get("model", {}))
    task = TaskConfig(**raw.get("task", {}))
    run = RunConfig(**raw.get("run", {}))
    docker = DockerConfig(**raw.get("docker", {}))
    reporting = ReportingConfig(**raw.get("reporting", {}))
    harnesses = raw.get("harnesses", ["opencode", "pi"])

    # Env var overrides (yaml < .env < CLI)
    if env_url := os.environ.get("MODEL_URL"):
        model.url = env_url
    if env_protocol := os.environ.get("MODEL_PROTOCOL"):
        model.protocol = env_protocol
    if env_name := os.environ.get("MODEL_NAME"):
        model.name = env_name
    if env_reps := os.environ.get("REPETITIONS"):
        run.repetitions = int(env_reps)
    if env_timeout := os.environ.get("TASK_TIMEOUT"):
        run.timeout_sec = int(env_timeout)

    # CLI overrides (highest priority)
    if "model_url" in cli_overrides:
        model.url = cli_overrides["model_url"]
    if "model_protocol" in cli_overrides:
        model.protocol = cli_overrides["model_protocol"]
    if "model_name" in cli_overrides:
        model.name = cli_overrides["model_name"]
    if "repetitions" in cli_overrides:
        run.repetitions = cli_overrides["repetitions"]
    if "timeout_sec" in cli_overrides:
        run.timeout_sec = cli_overrides["timeout_sec"]
    if "harnesses" in cli_overrides:
        harnesses = cli_overrides["harnesses"]
    if "languages" in cli_overrides:
        task.languages = cli_overrides["languages"]
    if "skip_existing" in cli_overrides:
        run.skip_existing = cli_overrides["skip_existing"]
    if "retry_failed" in cli_overrides:
        run.retry_failed = cli_overrides["retry_failed"]

    return Config(
        model=model,
        task=task,
        run=run,
        harnesses=harnesses,
        docker=docker,
        reporting=reporting,
        base_dir=config_path.parent,
    )
