# benchmark/task_loader.py
"""Load polyglot-benchmark exercises into structured Exercise objects."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Exercise:
    name: str
    language: str
    relpath: str
    solution_files: list[str]
    test_files: list[str]
    instructions_path: Path
    exercise_dir: Path


def load_exercises(
    polyglot_root: Path,
    languages: list[str] | None = None,
) -> list[Exercise]:
    """Discover all exercises under <lang>/exercises/practice/."""
    languages = languages or ["python", "javascript"]
    exercises: list[Exercise] = []

    for lang in languages:
        practice_dir = polyglot_root / lang / "exercises" / "practice"
        if not practice_dir.exists():
            continue

        for exercise_dir in sorted(practice_dir.iterdir()):
            if not exercise_dir.is_dir():
                continue

            config_path = exercise_dir / ".meta" / "config.json"
            instructions_path = exercise_dir / ".docs" / "instructions.md"

            if not config_path.exists() or not instructions_path.exists():
                continue

            config = json.loads(config_path.read_text())
            files = config.get("files", {})

            exercises.append(Exercise(
                name=exercise_dir.name,
                language=lang,
                relpath=str(exercise_dir.relative_to(polyglot_root)),
                solution_files=files.get("solution", []),
                test_files=files.get("test", []),
                instructions_path=instructions_path,
                exercise_dir=exercise_dir,
            ))

    return exercises
