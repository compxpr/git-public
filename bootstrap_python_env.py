#!/usr/bin/env python3
"""
bootstrap_python_env.py

Creates a local virtual environment, upgrades packaging tooling, and installs a
curated set of commonly-useful Python modules.

IMPORTANT NOTE ABOUT "Python 3.1.3":
- Python 3.1.x is end-of-life and is not realistically usable with modern pip/TLS/package indexes.
- This script targets modern Python (>= 3.11). If you actually meant Python 3.11.3, you're set.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import textwrap


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def python_exe_in_venv(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def pip_cmd(venv_py: Path) -> list[str]:
    return [str(venv_py), "-m", "pip"]


def ensure_modern_python(min_major: int = 3, min_minor: int = 11) -> None:
    v = sys.version_info
    if (v.major, v.minor) < (min_major, min_minor):
        msg = textwrap.dedent(
            f"""
            Detected Python {v.major}.{v.minor}.{v.micro} at: {sys.executable}

            This bootstrap script requires Python >= {min_major}.{min_minor}.

            If you truly meant "Python 3.1.3":
              - 3.1.x is end-of-life and will not work well with modern packaging.
              - Upgrade to a supported Python (3.11+ recommended).

            If you meant "Python 3.11.3":
              - Install/launch this script using that interpreter.
            """
        ).strip()
        raise SystemExit(msg)


PROFILES: dict[str, list[str]] = {
    # General "every project" utilities
    "core": [
        "rich",
        "python-dotenv",
        "pydantic",
        "typing-extensions",
        "tenacity",
        "loguru",
    ],
    # HTTP + APIs
    "http": [
        "requests",
        "httpx",
    ],
    # Developer tooling (format/lint/test/type-check)
    "dev": [
        "pytest",
        "pytest-cov",
        "ruff",
        "mypy",
        "ipython",
    ],
    # CLI building
    "cli": [
        "typer",
    ],
    # Data / analysis (bigger installs)
    "data": [
        "numpy",
        "pandas",
        "matplotlib",
    ],
}


def create_env_files(project_dir: Path) -> None:
    env_example = project_dir / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            textwrap.dedent(
                """\
                # Copy to ".env" and adjust values. Do not commit ".env".
                # Example:
                # API_KEY=your_key_here
                # LOG_LEVEL=INFO
                """
            ),
            encoding="utf-8",
        )

    gitignore = project_dir / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
    else:
        content = ""

    additions = [
        ".venv/",
        ".env",
        "__pycache__/",
        "*.pyc",
        ".pytest_cache/",
        ".mypy_cache/",
        ".ruff_cache/",
        ".DS_Store",
    ]
    changed = False
    for line in additions:
        if line not in content:
            content += ("" if content.endswith("\n") or content == "" else "\n") + line + "\n"
            changed = True

    if changed:
        gitignore.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap a Python project environment (.venv) and install useful modules."
    )
    parser.add_argument(
        "--venv",
        default=".venv",
        help='Virtual environment directory (default: ".venv")',
    )
    parser.add_argument(
        "--profile",
        action="append",
        choices=sorted(PROFILES.keys()) + ["all"],
        default=["core", "http", "dev"],
        help=(
            "Install a profile of packages. Can be used multiple times. "
            'Default: core,http,dev. Use "--profile all" for everything.'
        ),
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory to place .venv and helper files (default: current directory).",
    )
    parser.add_argument(
        "--lock",
        action="store_true",
        help="Write a requirements.lock using `pip freeze` after installs.",
    )
    args = parser.parse_args()

    ensure_modern_python()

    project_dir = Path(args.project_dir).resolve()
    venv_dir = (project_dir / args.venv).resolve()

    print(f"Platform: {platform.platform()}")
    print(f"Using interpreter: {sys.executable}")
    print(f"Project dir: {project_dir}")
    print(f"Venv dir: {venv_dir}")

    # Create venv
    if venv_dir.exists():
        print(f"\nVenv already exists at {venv_dir}")
    else:
        run([sys.executable, "-m", "venv", str(venv_dir)])

    venv_py = python_exe_in_venv(venv_dir)
    if not venv_py.exists():
        raise SystemExit(f"Could not find venv python at: {venv_py}")

    # Upgrade packaging tooling
    run(pip_cmd(venv_py) + ["install", "--upgrade", "pip", "setuptools", "wheel"])

    # Resolve package list
    selected = args.profile
    if "all" in selected:
        pkg_set = {p for prof in PROFILES.values() for p in prof}
    else:
        pkg_set = set()
        for name in selected:
            pkg_set.update(PROFILES[name])

    pkgs = sorted(pkg_set)

    print("\nInstalling packages:")
    for p in pkgs:
        print(f"  - {p}")

    run(pip_cmd(venv_py) + ["install"] + pkgs)

    # Helper files
    create_env_files(project_dir)

    # Optional lock file
    if args.lock:
        lock_path = project_dir / "requirements.lock"
        print(f"\nWriting lock file: {lock_path}")
        frozen = subprocess.check_output(pip_cmd(venv_py) + ["freeze"], text=True)
        lock_path.write_text(frozen, encoding="utf-8")

    # Print activation instructions
    print("\nNext steps:")
    if os.name == "nt":
        print(rf"  1) Activate: {venv_dir}\Scripts\activate")
    else:
        print(f"  1) Activate: source {venv_dir}/bin/activate")
    print("  2) Verify:   python -c \"import sys; print(sys.executable)\"")
    print("  3) Use .env: copy .env.example -> .env and set values")


if __name__ == "__main__":
    main()