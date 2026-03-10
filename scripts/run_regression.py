#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True, check=True)


def run_json(*args: str):
    return json.loads(run(*args).stdout)


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    fixture = ROOT / "fixtures" / "completed-relax"
    checked = run_json("scripts/check_qe_job.py", str(fixture), "--json")
    ensure(checked["completed"] is True, "fixture should be marked completed")
    ensure(checked["scf_converged"] is True, "fixture should be SCF converged")
    ensure(checked["ionic_converged"] is True, "fixture should be ionically converged")
    ensure(checked["warnings"] == [], "fixture should not emit warnings")

    summary = run_json("scripts/summarize_qe_run.py", str(fixture), "--json")
    ensure(abs(summary["final_energy_Ry"] + 15.4321) < 1e-6, "fixture energy should be parsed")

    failure = ROOT / "fixtures" / "scf-not-converged"
    checked_failure = run_json("scripts/check_qe_job.py", str(failure), "--json")
    ensure(checked_failure["completed"] is False, "failure fixture should not be marked completed")
    ensure(checked_failure["scf_converged"] is False, "failure fixture should not be SCF converged")
    ensure(any("requested threshold" in warning for warning in checked_failure["warnings"]), "failure fixture should report SCF non-convergence")
    recovery = run_json("scripts/recommend_qe_recovery.py", str(failure), "--json")
    ensure(recovery["severity"] == "warning", "SCF non-convergence should be a warning-level recovery case")
    ensure(any("mixing_beta" in action or "mixing" in action.lower() for action in recovery["recommended_actions"]), "recovery advice should mention SCF mixing")
    ensure(recovery["safe_to_reuse_existing_state"] is True, "SCF non-convergence should allow conditional scratch reuse")

    temp_dir = Path(tempfile.mkdtemp(prefix="qe-regression-"))
    proj_dir = Path(tempfile.mkdtemp(prefix="qe-projwfc-regression-"))
    try:
        run(
            "scripts/make_qe_inputs.py",
            str(temp_dir),
            "--task",
            "dos",
            "--species",
            "Si:28.0855:Si.UPF",
            "--scheduler",
            "none",
        )
        generated = run_json("scripts/check_qe_job.py", str(temp_dir), "--json")
        ensure(isinstance(generated, list) and len(generated) == 3, "generated DOS workflow should have three stages")
        ensure(generated[0]["task"] == "scf", "first generated stage should be scf")
        ensure(generated[1]["task"] == "nscf", "second generated stage should be nscf")
        ensure(generated[2]["task"] == "dos.x", "third generated stage should be dos.x")
        workflow_plan = (temp_dir / "WORKFLOW_PLAN.md").read_text()
        ensure("# Workflow Plan" in workflow_plan, "generated workflow should include WORKFLOW_PLAN.md")
        ensure("DOS" in workflow_plan, "workflow plan should describe the DOS stage")
        plan_path = Path(run("scripts/export_recovery_plan.py", str(failure), "--output", str(temp_dir / "RESTART_PLAN.md")).stdout.strip())
        plan_text = plan_path.read_text()
        ensure("# Recovery Plan" in plan_text, "exported plan should have a recovery-plan heading")
        ensure("mixing_beta" in plan_text or "SCF" in plan_text, "exported plan should include SCF recovery guidance")
        status_path = Path(run("scripts/export_status_report.py", str(failure), "--output", str(temp_dir / "STATUS_REPORT.md")).stdout.strip())
        status_text = status_path.read_text()
        ensure("# Status Report" in status_text, "exported status should have a status-report heading")
        ensure("SCF did not reach the requested threshold." in status_text, "status report should include SCF warning text")
        suggest_path = Path(run("scripts/export_input_suggestions.py", str(failure), "--output", str(temp_dir / "INPUT_SUGGESTIONS.md")).stdout.strip())
        suggest_text = suggest_path.read_text()
        ensure("# Input Suggestions" in suggest_text, "exported suggestions should have an input-suggestions heading")
        ensure("mixing_beta = 0.20" in suggest_text, "QE suggestions should include a conservative mixing_beta recommendation")
        run(
            "scripts/make_qe_inputs.py",
            str(proj_dir),
            "--task",
            "projwfc",
            "--species",
            "Si:28.0855:Si.UPF",
            "--scheduler",
            "none",
        )
        proj = run_json("scripts/check_qe_job.py", str(proj_dir), "--json")
        ensure(isinstance(proj, list) and len(proj) == 3, "generated projwfc workflow should have three stages")
        ensure(proj[2]["task"] == "projwfc.x", "third generated stage should be projwfc.x")
        proj_plan = (proj_dir / "WORKFLOW_PLAN.md").read_text()
        ensure("projwfc.x" in proj_plan, "workflow plan should describe the projwfc stage")
    finally:
        shutil.rmtree(temp_dir)
        shutil.rmtree(proj_dir)

    print("qe-workflows regression passed")


if __name__ == "__main__":
    main()
