#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from check_qe_job import discover_dirs
from dft_parsers import parse_qe_dir


def render_record(record: dict[str, object]) -> str:
    warnings = list(record.get("warnings") or [])
    name = Path(str(record["path"])).name
    lines = [f"## {name}", ""]

    if any("requested threshold" in warning for warning in warnings):
        lines.extend(
            [
                "Conservative QE snippet for SCF stabilization:",
                "",
                "```text",
                "&ELECTRONS",
                "  mixing_beta = 0.20,",
                "  conv_thr = 1.0d-8,",
                "/",
                "# Review occupations and smearing choices before rerunning.",
                "```",
                "",
            ]
        )

    if any("Referenced pseudopotential not found" in warning for warning in warnings):
        lines.extend(
            [
                "No safe direct pw.x patch is enough here.",
                "",
                "```text",
                "# Restore the missing .UPF file or correct pseudo_dir and ATOMIC_SPECIES.",
                "```",
                "",
            ]
        )

    if any("diagonalization routine failed" in warning.lower() or "ill-conditioned" in warning.lower() for warning in warnings):
        lines.extend(
            [
                "Prefer a conservative clean restart after correcting the root cause:",
                "",
                "```text",
                "&ELECTRONS",
                "  mixing_beta = 0.20,",
                "/",
                "# Recheck structure, pseudopotentials, and cutoffs before rerunning.",
                "```",
                "",
            ]
        )

    if len(lines) == 2:
        lines.extend(["No conservative input snippet was required for this path.", ""])

    return "\n".join(lines)


def render_markdown(records: list[dict[str, object]], source: Path) -> str:
    lines = ["# Input Suggestions", "", f"Source: `{source}`", ""]
    for index, record in enumerate(records):
        lines.append(render_record(record).rstrip())
        if index != len(records) - 1:
            lines.extend(["", "---", ""])
    return "\n".join(lines).rstrip() + "\n"


def default_output(source: Path) -> Path:
    if source.is_file():
        return source.parent / f"{source.stem}.INPUT_SUGGESTIONS.md"
    return source / "INPUT_SUGGESTIONS.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export conservative QE input suggestion snippets.")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()

    source = Path(args.path).expanduser().resolve()
    records = [parse_qe_dir(directory) for directory in discover_dirs(source)]
    output = Path(args.output).expanduser().resolve() if args.output else default_output(source)
    output.write_text(render_markdown(records, source))
    print(output)


if __name__ == "__main__":
    main()
