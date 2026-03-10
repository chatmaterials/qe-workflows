---
name: "qe-workflows"
description: "Use when the task involves Quantum ESPRESSO workflows, including pw.x input preparation, scf, relax, dos.x, projwfc.x, and bands.x setups, pseudopotential and scratch layout checks, restart handling, pw.x output review, convergence checks, and Slurm or PBS job scripts."
---

# QE Workflows

This skill handles practical Quantum ESPRESSO setup, review, and recovery. Use it when the request is clearly about `pw.x`, `dos.x`, `bands.x`, `.UPF` management, or QE stage orchestration.

## When to use

Use this skill when the user mentions or implies:

- `Quantum ESPRESSO`, `QE`, `pw.x`, `dos.x`, `bands.x`, `projwfc.x`, `.UPF`
- `scf`, `relax`, `vc-relax`, `nscf`, DOS, band structure, restart, or scheduler scripts in QE
- `ecutwfc`, `ecutrho`, `occupations`, `degauss`, `prefix`, `pseudo_dir`, `outdir`, or scratch-tree issues

## Operating stance

Prioritize missing information in this order:

1. task: `scf`, `relax`, `dos`, `band`, or restart
2. pseudo family and exchange-correlation consistency
3. occupations, smearing, and whether the system is metallic or not
4. parent-child file flow through `prefix`, `pseudo_dir`, and `outdir`
5. scheduler and MPI launcher

Never silently invent:

- `.UPF` filenames, versions, or pseudo families
- whether a system should be fixed occupations or smearing when the class is unclear
- a band path without a real source
- whether missing QE scratch data can be reconstructed when it is gone

## Workflow

### 1. Classify the request

- **Setup**: generate or edit QE inputs and stage layout.
- **Review**: inspect an existing QE directory and summarize status.
- **Recovery**: identify the likely failure mode and recommend the smallest safe restart.

### 2. Gather the minimum viable context

Before recommending settings, establish:

- structure source and whether the system is bulk, slab, or molecule-in-box
- target observable: relaxed geometry, total energy, DOS, or band structure
- pseudo policy and whether a standard pseudo family already exists
- whether the system is metallic, insulating, magnetic, or unknown
- scheduler environment and scratch handling

### 3. Use the bundled helpers

- `scripts/make_qe_inputs.py`
  Generate conservative `scf`, `relax`, `dos`, `projwfc`, or `band` workflow skeletons.
- `scripts/check_qe_job.py`
  Check one QE directory or staged workflow root for missing inputs and pseudo or restart dependencies.
- `scripts/summarize_qe_run.py`
  Summarize a QE run using the input and `pw.x` output.
- `scripts/recommend_qe_recovery.py`
  Turn incomplete or failed QE runs into concrete restart and recovery guidance.
- `scripts/export_status_report.py`
  Export a shareable markdown status report from a QE run or staged workflow.
- `scripts/export_input_suggestions.py`
  Export conservative QE input snippets based on detected recovery patterns.

### 4. Load focused references only when needed

- QE workflow and file guidance: `references/qe.md`
- convergence planning: `references/convergence.md`
- QE failures and restarts: `references/failure-modes.md`
- scheduler notes: `references/schedulers.md`

### 5. Deliver an auditable answer

Whenever you recommend edits or restarts, include:

- the assumed task and parent-child stage relationship
- unresolved physics choices the user must still confirm
- exact files changed or generated
- what scratch or output artifacts must exist before the next stage can run

## Guardrails

- DOS and band workflows are dependent child calculations, not first calculations.
- Keep `prefix`, `pseudo_dir`, and `outdir` consistent across related stages.
- If the workflow depends on scratch data that is gone, say plainly that the parent stage may need to rerun.
- If the band path is unresolved, say so instead of fabricating one.

## Quality bar

- Prefer conservative defaults over flashy guesses.
- Distinguish QE syntax advice from material-specific physics advice.
- Diagnose from the actual logs when logs are available.
