"""Invoke task definitions for Strike Pilot.

Available tasks:
    lint         - Run ruff linter
    format       - Run ruff formatter
    test         - Run pytest test suite
    check        - Run lint and test together
    docker-build - Build the Docker image
    docker-run   - Run the API server in a container
    docker-clean - Remove the local Docker image
"""

from invoke import Collection, task

IMAGE_NAME = "strike-pilot"
IMAGE_TAG = "latest"
_IMAGE = f"{IMAGE_NAME}:{IMAGE_TAG}"


@task
def lint(ctx):  # type: ignore[no-untyped-def]
    """Run ruff linter on source and tests."""
    ctx.run("ruff check src tests", pty=True)


@task
def format(ctx):  # type: ignore[no-untyped-def]
    """Run ruff formatter on source and tests."""
    ctx.run("ruff format src tests", pty=True)


@task
def format_check(ctx):  # type: ignore[no-untyped-def]
    """Check ruff formatting without making changes (CI gate)."""
    ctx.run("ruff format --check src tests", pty=True)


@task
def mypy(ctx):  # type: ignore[no-untyped-def]
    """Run mypy strict type checker on source."""
    ctx.run("mypy src", pty=True)


@task
def test(ctx):  # type: ignore[no-untyped-def]
    """Run pytest test suite."""
    ctx.run("pytest tests/ -v", pty=True)


@task(pre=[lint, format_check, mypy, test])
def check(ctx):  # type: ignore[no-untyped-def]
    """Run lint, format check, type check, and tests together."""
    print("All checks passed.")


@task(
    help={
        "tag": "Image tag (default: latest)",
        "no_cache": "Disable Docker layer cache",
    }
)
def docker_build(ctx, tag=IMAGE_TAG, no_cache=False):  # type: ignore[no-untyped-def]
    """Build the Strike Pilot Docker image."""
    image = f"{IMAGE_NAME}:{tag}"
    cache_flag = "--no-cache" if no_cache else ""
    ctx.run(f"docker build {cache_flag} -t {image} .", pty=True)


@task(
    help={
        "port": "Host port to bind (default: 8000)",
        "tag": "Image tag to run (default: latest)",
    }
)
def docker_run(ctx, port=8000, tag=IMAGE_TAG):  # type: ignore[no-untyped-def]
    """Run the API server in a Docker container."""
    image = f"{IMAGE_NAME}:{tag}"
    ctx.run(f"docker run --rm -p {port}:8000 {image}", pty=True)


@task(
    help={"tag": "Image tag to remove (default: latest)"},
)
def docker_clean(ctx, tag=IMAGE_TAG):  # type: ignore[no-untyped-def]
    """Remove the local Strike Pilot Docker image."""
    image = f"{IMAGE_NAME}:{tag}"
    ctx.run(f"docker rmi {image}", pty=True)


ns = Collection(lint, format, format_check, mypy, test, check, docker_build, docker_run, docker_clean)
