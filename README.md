# DES Example Implementations

This repository is a collection of example implementations for discrete-event
systems (DES). It serves as the top-level workspace for several DES examples,
experiments, and supporting utilities.

## Projects

- `on-the-fly_nonblocking/` contains Python examples for on-the-fly
  non-deadlock analysis on deterministic finite automata (DFA), including
  full-observation and partial-observation examples.
- `detectab;e_nonblocking/` contains examples and utilities related to
  detectability and cognitive nonblocking DES analysis.

Each subdirectory may include its own README, runnable examples, and generated
visualization outputs.

## Environment

Use a local Python environment for dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If a subproject does not provide a `requirements.txt`, install the dependencies
listed in that subproject's README.

## Notes

The root `.gitignore` excludes local environments, IDE settings, Python cache
files, logs, and generated output folders so that only source code, examples,
documentation, and intentional artifacts are tracked.
