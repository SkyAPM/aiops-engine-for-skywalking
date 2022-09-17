# Setup Your Development Environment

We utilize [Poetry](https://python-poetry.org/) to manage the dependencies and virtual environments in the project.

First of all, you need to install Poetry. Please refer to
the [official documentation](https://python-poetry.org/docs/#installation) for the installation.

Before you have the dependencies installed, you need to set up to have a `.venv` virtualenv at the root of the project.
Then Poetry will automatically use it as the virtual environment.

Next, you can install the dependencies and create the virtual environment by running the following command:

```bash
poetry install
```

When you need to add a new dependency (actual dependency or dev-dependency), refer to
[the official documentation](https://python-poetry.org/docs/cli/#add) for the usage to keep them
in different sections of the `pyproject.toml` file, so it doesn't introduce additional
dependencies to the production environment.

**Always make sure the dependencies are correctly recorded, and you should push both `pyproject.toml` and `poetry.lock`
to the repository.**

## Lint

Refer to our coding style guide [here](CodingStyle.md) for running the linter and fixing common convention problems.

## Make

Many of the essential commands are automated through `Makefile`, remember to have `make` installed in your system.

## Run the Unit Tests

TBD - We are working on the unit tests.

## Run the Integration Tests

TBD - We are working on the integration tests.

## Run the End-to-End Tests

TBD - We are working on the end-to-end tests.