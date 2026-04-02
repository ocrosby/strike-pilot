"""Invoke task definitions for Strike Pilot.

Available tasks:
    lint    - Run ruff linter
    format  - Run ruff formatter
    test    - Run pytest test suite
    check   - Run lint and test together
"""

from invoke import Collection, task


@task
def lint(ctx):  # type: ignore[no-untyped-def]
    """Run ruff linter on source and tests."""
    ctx.run("ruff check src tests", pty=True)


@task
def format(ctx):  # type: ignore[no-untyped-def]
    """Run ruff formatter on source and tests."""
    ctx.run("ruff format src tests", pty=True)


@task
def test(ctx):  # type: ignore[no-untyped-def]
    """Run pytest test suite."""
    ctx.run("pytest tests/ -v", pty=True)


@task(pre=[lint, test])
def check(ctx):  # type: ignore[no-untyped-def]
    """Run lint and tests together."""
    print("All checks passed.")


ns = Collection(lint, format, test, check)
