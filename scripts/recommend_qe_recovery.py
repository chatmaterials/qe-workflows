#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_qe_job import discover_dirs
from dft_parsers import parse_qe_dir


def build_recommendation(record: dict[str, object]) -> dict[str, object]:
    warnings = list(record.get("warnings") or [])
    missing_inputs = list(record.get("missing_inputs") or [])
    actions: list[str] = []
    issues: list[str] = []
    severity = "info"
    safe_restart = False
    restart_strategy = "No recovery action is needed yet."

    if missing_inputs:
        severity = "error"
        issues.append("The directory is missing a QE input file.")
        actions.append("Create or restore the required pw.x input before attempting a run or restart.")

    if record.get("state") == "template":
        issues.append("This stage is still a template and is not ready to run.")
        actions.append("Replace the placeholder bands path or template values before launching the stage.")
        restart_strategy = "Do not restart this stage yet; finish the template setup first."

    if any("Referenced pseudopotential not found" in warning for warning in warnings):
        severity = "error"
        issues.append("A required pseudopotential file is missing.")
        actions.append("Restore the missing .UPF file or correct pseudo_dir and file naming before rerunning.")
        restart_strategy = "Do not restart until the pseudopotential set is complete and consistent."

    if any("requested threshold" in warning for warning in warnings):
        severity = "warning" if severity == "info" else severity
        issues.append("The SCF loop failed to meet the requested threshold.")
        actions.append("Inspect occupations, smearing, mixing_beta, and cutoff choices before only increasing iteration counts.")
        actions.append("If the model assumptions are sound, retry with a smaller mixing_beta or a more conservative SCF setup.")
        restart_strategy = "Adjust the SCF settings first, then restart using the existing outdir only if the scratch tree is still consistent."
        safe_restart = True

    if any("diagonalization routine failed" in warning.lower() or "ill-conditioned" in warning.lower() for warning in warnings):
        severity = "error"
        issues.append("A diagonalization or overlap-matrix failure was detected.")
        actions.append("Inspect the structure and the pseudo or cutoff consistency before rerunning.")
        actions.append("Prefer a clean restart after correcting the root cause instead of blindly trusting the old scratch state.")
        restart_strategy = "Prefer a clean restart from corrected inputs; do not rely on suspect scratch data."
        safe_restart = False

    if record.get("task") in {"nscf", "bands", "bands.x", "dos.x"} and not record.get("completed"):
        issues.append("This child stage depends on a consistent parent prefix and outdir.")
        actions.append("Verify that the parent SCF stage completed and that prefix and outdir still point to the same scratch tree.")
        if severity == "info":
            severity = "warning"

    if record.get("state") == "incomplete" and not issues:
        severity = "warning"
        issues.append("The calculation stopped before completion.")
        actions.append("Check scheduler logs, walltime, and the integrity of the QE scratch directory before restarting.")
        restart_strategy = "Reuse the existing outdir only if the scratch contents are intact and the physics model is unchanged."
        safe_restart = True

    if not issues:
        issues.append("No critical recovery issues were detected.")
        actions.append("Proceed with the next planned stage or post-processing step.")

    return {
        "path": record["path"],
        "task": record["task"],
        "state": record["state"],
        "severity": severity,
        "issues": issues,
        "recommended_actions": actions,
        "restart_strategy": restart_strategy,
        "safe_to_reuse_existing_state": safe_restart,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Recommend QE recovery or restart actions from a run directory.")
    parser.add_argument("directory", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.directory).expanduser().resolve()
    records = [build_recommendation(parse_qe_dir(directory)) for directory in discover_dirs(root)]
    if args.json:
        print(json.dumps(records if len(records) > 1 else records[0], indent=2))
        return
    for index, record in enumerate(records):
        if index:
            print()
        print(f"[{Path(str(record['path'])).name}] {record['severity']} {record['task']} {record['state']}")
        print("Issues: " + "; ".join(record["issues"]))
        for action in record["recommended_actions"]:
            print("- " + action)
        print("Restart strategy: " + record["restart_strategy"])


if __name__ == "__main__":
    main()
