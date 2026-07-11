# tests/test_config.py
from pathlib import Path
from textwrap import dedent

from benchmark.config import Config, load_config


def test_load_config_from_yaml(tmp_path):
    yaml_content = dedent("""
        model:
          url: https://open.bigmodel.cn/api/paas/v4/
          protocol: openai
          name: glm-5.2
          api_key_env: LLM_API_KEY

        task:
          source: polyglot
          languages: [python, javascript]
          addendum: "Don't rename functions."

        run:
          repetitions: 3
          timeout_sec: 600
          skip_existing: true
          parallel: 1

        harnesses: [opencode, pi]

        docker:
          image: harness:latest
          results_volume: ./results

        reporting:
          output: [sqlite, html, markdown]
          pages_path: docs
          auto_commit: true
    """)
    config_file = tmp_path / "benchmark.yaml"
    config_file.write_text(yaml_content)

    config = load_config(config_file)

    assert config.model.url == "https://open.bigmodel.cn/api/paas/v4/"
    assert config.model.protocol == "openai"
    assert config.model.name == "glm-5.2"
    assert config.run.repetitions == 3
    assert config.harnesses == ["opencode", "pi"]
    assert config.task.languages == ["python", "javascript"]


def test_cli_overrides(tmp_path, monkeypatch):
    yaml_content = dedent("""
        model:
          url: https://default.example.com
          protocol: openai
          name: default-model
          api_key_env: LLM_API_KEY
        task:
          source: polyglot
          languages: [python]
          addendum: ""
        run:
          repetitions: 1
          timeout_sec: 300
          skip_existing: false
          parallel: 1
        harnesses: [opencode]
        docker:
          image: harness:latest
          results_volume: ./results
        reporting:
          output: [sqlite]
          pages_path: docs
          auto_commit: false
    """)
    config_file = tmp_path / "benchmark.yaml"
    config_file.write_text(yaml_content)

    config = load_config(
        config_file,
        cli_overrides={"model_url": "https://override.example.com", "repetitions": 5},
    )

    assert config.model.url == "https://override.example.com"
    assert config.run.repetitions == 5


def test_env_overrides(tmp_path, monkeypatch):
    yaml_content = dedent("""
        model:
          url: https://yaml-default.example.com
          protocol: openai
          name: yaml-model
          api_key_env: LLM_API_KEY
        task:
          source: polyglot
          languages: [python]
          addendum: ""
        run:
          repetitions: 1
          timeout_sec: 300
          skip_existing: false
          parallel: 1
        harnesses: [opencode]
        docker:
          image: harness:latest
          results_volume: ./results
        reporting:
          output: [sqlite]
          pages_path: docs
          auto_commit: false
    """)
    config_file = tmp_path / "benchmark.yaml"
    config_file.write_text(yaml_content)

    monkeypatch.setenv("MODEL_URL", "https://env-override.example.com")
    monkeypatch.setenv("MODEL_NAME", "env-model")

    config = load_config(config_path=config_file)

    assert config.model.url == "https://env-override.example.com"
    assert config.model.name == "env-model"


def test_cli_beats_env(tmp_path, monkeypatch):
    yaml_content = dedent("""
        model:
          url: https://yaml.example.com
          protocol: openai
          name: yaml-model
          api_key_env: LLM_API_KEY
        task: {source: polyglot, languages: [python], addendum: ""}
        run: {repetitions: 1, timeout_sec: 300, skip_existing: false, parallel: 1}
        harnesses: [opencode]
        docker: {image: harness:latest, results_volume: ./results}
        reporting: {output: [sqlite], pages_path: docs, auto_commit: false}
    """)
    config_file = tmp_path / "benchmark.yaml"
    config_file.write_text(yaml_content)

    monkeypatch.setenv("MODEL_URL", "https://env.example.com")
    config = load_config(
        config_path=config_file,
        cli_overrides={"model_url": "https://cli.example.com"},
    )

    assert config.model.url == "https://cli.example.com"
