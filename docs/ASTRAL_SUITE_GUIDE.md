# The Astral Suite: Modern Python Development with uv, ruff, and typer

## Overview

docling-testing fully leverages the Astral suite of tools for modern, fast Python development:
- **uv** - Ultra-fast Python package management (10-100x faster than pip)
- **ruff** - Lightning-fast Python linter and formatter
- **typer** - Modern CLI framework (we use ty for type checking)

## uv: The Package Manager

### Why uv Over pip?

- **Speed**: 10-100x faster than pip and pip-tools
- **All-in-one**: Replaces pip, pip-tools, pipx, poetry, pyenv, virtualenv
- **Deterministic**: Lock files ensure reproducible builds
- **Space-efficient**: Global cache prevents duplicate downloads

### Essential uv Commands

#### Project Setup
```bash
# Initialize new project
uv init

# Sync dependencies from pyproject.toml
uv sync

# Add a dependency
uv add torch transformers

# Add dev dependency
uv add --dev pytest

# Remove dependency
uv remove package-name
```

#### Virtual Environments
```bash
# uv automatically creates venvs, but you can be explicit
uv venv .venv

# Run commands in the project environment
uv run python script.py
uv run pytest
```

#### Python Version Management
```bash
# List available Python versions
uv python list

# Install specific Python version
uv python install 3.13

# Pin project to Python version
uv python pin 3.13
```

#### Dependency Management
```bash
# View dependency tree
uv tree

# Update all dependencies
uv lock --upgrade

# Update specific package
uv lock --upgrade-package transformers

# Show outdated packages
uv pip list --outdated
```

### In Containers

Always use uv in containers instead of pip:

```dockerfile
# Install uv in container
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create venv and install deps
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --python /opt/venv/bin/python -r requirements.txt

# Or with pyproject.toml
COPY pyproject.toml .
RUN uv sync --no-dev
```

## ruff: The Linter/Formatter

### Configuration

In `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py313"
line-length = 100
fix = true

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
]
ignore = ["E501"]  # line too long (handled by formatter)

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Usage

```bash
# Check and auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Both in one command
ruff check --fix . && ruff format .

# Watch mode for development
ruff check --watch
```

### Pre-commit Integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## typer: Modern CLI Framework

### Basic CLI Structure

```python
#!/usr/bin/env python3
"""Training script using typer."""

import typer
from typing import Optional
from pathlib import Path

app = typer.Typer(help="DoclingBERT Training CLI")

@app.command()
def train(
    checkpoint: Optional[str] = typer.Option(None, help="Checkpoint to resume from"),
    steps: int = typer.Option(100, help="Training steps"),
    force: bool = typer.Option(False, "--force", "-f", help="Force retrain"),
):
    """Train multiclass classifier."""
    if force:
        typer.echo("Force retraining...")
    typer.echo(f"Training for {steps} steps")
    # Implementation here

@app.command()
def evaluate(
    checkpoint: Path = typer.Argument(..., help="Path to checkpoint"),
    output: Optional[Path] = typer.Option(None, help="Save metrics to file"),
):
    """Evaluate model checkpoint."""
    with typer.progressbar(range(100)) as progress:
        for item in progress:
            # Process evaluation
            pass

if __name__ == "__main__":
    app()
```

### Advanced Features

```python
# Rich output formatting
from rich.console import Console
from rich.table import Table

console = Console()

@app.command()
def status():
    """Show training status."""
    table = Table(title="Model Performance")
    table.add_column("Class", style="cyan")
    table.add_column("Precision", justify="right")
    table.add_column("Recall", justify="right")
    table.add_column("F1", justify="right")

    table.add_row("body_text", "0.85", "0.83", "0.84")
    table.add_row("footnote", "0.92", "0.89", "0.90")
    table.add_row("heading", "0.88", "0.91", "0.89")

    console.print(table)

# Async commands
@app.command()
async def download_corpus():
    """Async corpus download."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://arxiv.org/api/...")
        typer.echo(response.json())
```

## Complete Development Workflow

### 1. Project Setup
```bash
# Create project with uv
uv init docling-testing
cd docling-testing

# Add dependencies
uv add torch transformers datasets
uv add --dev pytest ruff

# Pin Python version
uv python pin 3.13
```

### 2. Development Commands
```bash
# Install all deps
uv sync

# Run training
uv run python scripts/training/train_multiclass_classifier.py

# Lint and format
ruff check --fix . && ruff format .

# Run tests
uv run pytest

# Build distribution
uv build
```

### 3. CI/CD Integration
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync

      - name: Lint
        run: |
          uv run ruff check .
          uv run ruff format --check .

      - name: Test
        run: uv run pytest
```

### 4. Container Best Practices

```dockerfile
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy source
COPY . .

# Install project
RUN uv sync --frozen

# Run with uv
CMD ["uv", "run", "python", "-m", "docling_testing"]
```

## docling-testing Specific Usage

### Running Training Scripts
```bash
# Always use uv run
uv run python scripts/training/train_multiclass_classifier.py

# Run with specific Python
uv run --python 3.13 python scripts/training/train_rebalanced.py

# Run evaluation
uv run python scripts/evaluation/evaluate_checkpoint.py --checkpoint models/v2/checkpoint-100
```

### Adding New Dependencies
```bash
# Instead of: pip install docling
uv add docling

# Add OCR engines
uv add easyocr tesserocr

# Instead of: pip install -e .
uv pip install -e .

# Instead of: pip freeze
uv pip freeze
```

### Tool Management
```bash
# Install tools in isolated environments
uv tool install ruff
uv tool install black
uv tool run pytest

# Or use in project
uv run --with black black .
```

## Performance Tips

1. **Use uv for everything** - It's faster and more reliable than pip
2. **Enable caching** - uv automatically caches packages globally
3. **Lock dependencies** - Use `uv.lock` for reproducible builds
4. **Parallel operations** - uv handles concurrent installs automatically
5. **Minimal rebuilds** - uv only reinstalls changed dependencies

## Common Pitfalls to Avoid

❌ **Don't use pip directly**
```bash
# Bad
pip install docling

# Good
uv add docling
```

❌ **Don't mix package managers**
```bash
# Bad
pip install paddleocr
uv add easyocr

# Good - use uv for everything
uv add paddleocr easyocr
```

❌ **Don't ignore lock files**
```bash
# Bad
uv sync --no-lock

# Good
uv sync --frozen  # Use exact locked versions
```

## Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [typer Documentation](https://typer.tiangolo.com/)
- [uv Cheatsheet](https://mathspp.com/blog/uv-cheatsheet)

## Summary

The Astral suite provides a modern, fast, and consistent Python development experience:
- **uv** handles all package management 10-100x faster than traditional tools
- **ruff** provides instant linting and formatting
- **typer** makes building CLIs intuitive and type-safe

By fully adopting these tools, docling-testing achieves faster development cycles, more reliable builds, and a better developer experience.
