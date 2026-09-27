import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(code: str, env_file: str | None, extra_env: dict | None = None):
    target = ROOT / ".env"
    existing = target.read_text() if target.exists() else None
    if env_file is not None:
        target.write_text(env_file)
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r})\n{code}"],
            capture_output=True, text=True,
            env={**os.environ, **(extra_env or {})}, cwd=ROOT)
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()
    finally:
        if existing is not None:
            target.write_text(existing)
        elif target.exists():
            target.unlink()


def test_values_load_from_the_env_file():
    out = run("import env, os; print(os.environ['PEXELS_API_KEY'])",
              "PEXELS_API_KEY=from-file\n")
    assert out == "from-file"


def test_exported_variables_win_over_the_file():
    out = run("import env, os; print(os.environ['MLP_LLM_MODEL'])",
              "MLP_LLM_MODEL=from-file\n", {"MLP_LLM_MODEL": "from-shell"})
    assert out == "from-shell"


def test_missing_env_file_is_not_an_error():
    out = run("import env; print('loaded')", None)
    assert out == "loaded"


def test_example_documents_every_variable_the_code_reads():
    import re

    example = (ROOT / ".env.example").read_text()
    documented = set(re.findall(r"^([A-Z_]+)=", example, re.M))

    used = set()
    for path in list(ROOT.glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        used |= set(re.findall(r'(?:environ\.get|\btext)\("([A-Z_]+)"', path.read_text()))
    assert used <= documented, f"undocumented: {sorted(used - documented)}"
