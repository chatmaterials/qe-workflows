#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from check_qe_job import discover_dirs
from dft_parsers import parse_qe_dir
from recommend_qe_recovery import build_recommendation


def render_markdown(records: list[tuple[dict[str, object], dict[str, object]]], source: Path) -> str:
    lines = ["# Status Report", "", f"Source: `{source}`", ""]
    for index, (record, recovery) in enumerate(records):
        name = Path(str(record["path"])).name
        lines.extend(
            [
                f"## {name}",
                "",
                f"- Task: `{record['task']}`",
                f"- State: `{record['state']}`",
                f"- Recovery severity: `{recovery['severity']}`",
                f"- Completed: `{str(record['completed']).lower()}`",
                f"- SCF converged: `{str(record['scf_converged']).lower()}`",
                f"- Ionic converged: `{str(record['ionic_converged']).lower()}`",
            ]
        )
        if record.get("final_energy_Ry") is not None:
            lines.append(f"- Final energy (Ry): `{record['final_energy_Ry']:.8f}`")
        if record.get("total_force_Ry_bohr") is not None:
            lines.append(f"- Total force (Ry/bohr): `{record['total_force_Ry_bohr']:.6f}`")
        lines.extend(["", "### Missing Inputs"])
        missing = record.get("missing_inputs") or []
        lines.extend(f"- {item}" for item in missing) if missing else lines.append("- None")
        lines.extend(["", "### Warnings"])
        warnings = record.get("warnings") or []
        lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
        lines.extend(["", "### Recommended Actions"])
        lines.extend(f"- {item}" for item in recovery["recommended_actions"])
        lines.extend(["", "### Restart Strategy", recovery["restart_strategy"], ""])
        if index != len(records) - 1:
            lines.append("---")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def default_output(source: Path) -> Path:
    if source.is_file():
        return source.parent / f"{source.stem}.STATUS_REPORT.md"
    return source / "STATUS_REPORT.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a markdown status report for a QE run or staged workflow.")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()

    source = Path(args.path).expanduser().resolve()
    records = []
    for directory in discover_dirs(source):
        parsed = parse_qe_dir(directory)
        records.append((parsed, build_recommendation(parsed)))
    output = Path(args.output).expanduser().resolve() if args.output else default_output(source)
    output.write_text(render_markdown(records, source))
    print(output)


if __name__ == "__main__":
    main()
