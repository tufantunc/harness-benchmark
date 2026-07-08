# tests/test_task_loader.py
from benchmark.task_loader import Exercise, load_exercises


def test_load_exercises(tmp_path):
    polyglot = tmp_path / "polyglot-benchmark"
    py_practice = polyglot / "python" / "exercises" / "practice"
    py_practice.mkdir(parents=True)

    exercise = py_practice / "leap"
    exercise.mkdir()
    (exercise / ".docs").mkdir()
    (exercise / ".docs" / "instructions.md").write_text("Implement leap year.")
    (exercise / ".meta").mkdir()
    (exercise / ".meta" / "config.json").write_text(
        '{"files": {"solution": ["leap.py"], "test": ["leap_test.py"], "example": [".meta/example.py"]}}'
    )
    (exercise / "leap.py").write_text("def leap_year(year):\n    pass\n")

    exercises = load_exercises(polyglot, languages=["python"])

    assert len(exercises) == 1
    assert exercises[0].name == "leap"
    assert exercises[0].language == "python"
    assert exercises[0].solution_files == ["leap.py"]
    assert exercises[0].test_files == ["leap_test.py"]
    assert "leap" in exercises[0].relpath


def test_load_exercises_filters_language(tmp_path):
    polyglot = tmp_path / "polyglot-benchmark"
    for lang in ["python", "javascript"]:
        practice = polyglot / lang / "exercises" / "practice" / "test-ex"
        practice.mkdir(parents=True)
        (practice / ".docs").mkdir()
        (practice / ".docs" / "instructions.md").write_text("Do something.")
        (practice / ".meta").mkdir()
        ext = ".py" if lang == "python" else ".js"
        test_ext = "_test.py" if lang == "python" else ".spec.js"
        (practice / ".meta" / "config.json").write_text(
            f'{{"files": {{"solution": ["test-ex{ext}"], "test": ["test-ex{test_ext}"]}}}}'
        )
        (practice / f"test-ex{ext}").write_text("pass")

    only_python = load_exercises(polyglot, languages=["python"])
    assert len(only_python) == 1
    assert only_python[0].language == "python"

    both = load_exercises(polyglot, languages=["python", "javascript"])
    assert len(both) == 2
