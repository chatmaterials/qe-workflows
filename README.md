# qe-workflows

[![CI](https://img.shields.io/github/actions/workflow/status/chatmaterials/qe-workflows/ci.yml?branch=main&label=CI)](https://github.com/chatmaterials/qe-workflows/actions/workflows/ci.yml) [![Release](https://img.shields.io/github/v/release/chatmaterials/qe-workflows?display_name=tag)](https://github.com/chatmaterials/qe-workflows/releases)

Standalone skill for Quantum ESPRESSO workflow setup, review, convergence checks, and restart handling.

## What This Skill Covers

- `scf`, `relax`, `dos`, `projwfc`, and `band` workflow skeletons
- directory checks for missing inputs, missing `.UPF` references, and broken staged dependencies
- quick summaries from QE input and `pw.x` output
- recovery recommendations for incomplete or non-converged runs
- conservative scheduler-script generation for Slurm and PBS

## What It Does Not Do

- it does not guess `.UPF` filenames, pseudo families, or `ecutwfc` and `ecutrho` policies without context
- it does not fabricate a band path for unknown structures
- it does not pretend missing QE scratch trees can always be recovered

## Install

```bash
npx skills add chatmaterials/qe-workflows -g -y
```

## Local Validation

```bash
python3 -m py_compile scripts/*.py
npx skills add . --list
python3 scripts/make_qe_inputs.py /tmp/qe-test --task band --species 'Si:28.0855:Si.UPF' --scheduler none
python3 scripts/check_qe_job.py /tmp/qe-test
python3 scripts/recommend_qe_recovery.py fixtures/scf-not-converged
python3 scripts/export_recovery_plan.py fixtures/scf-not-converged
python3 scripts/export_status_report.py fixtures/scf-not-converged
python3 scripts/export_input_suggestions.py fixtures/scf-not-converged
python3 scripts/run_regression.py
```

## First Release Checklist

1. Initialize a fresh repository from this directory.
2. Run the local validation commands from this directory.
3. Commit the repo root as the first release candidate.
4. Tag the first release, for example `v0.1.0`.

## Suggested First Commit

```bash
git init
git add .
git commit -m "Initial release of qe-workflows"
git tag v0.1.0
```
