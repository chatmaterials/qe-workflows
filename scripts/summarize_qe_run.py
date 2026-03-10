#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dft_parsers import parse_qe_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a QE run directory.")
    parser.add_argument("directory", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    record = parse_qe_dir(Path(args.directory).expanduser().resolve())
    if args.json:
        print(json.dumps(record, indent=2))
        return
    print(f"Path: {record['path']}")
    print(f"Task: {record['task']}")
    print(f"State: {record['state']}")
    if record.get("final_energy_Ry") is not None:
        print(f"Final energy: {record['final_energy_Ry']:.8f} Ry")
    if record.get("total_force_Ry_bohr") is not None:
        print(f"Total force: {record['total_force_Ry_bohr']:.6f} Ry/bohr")
    print(f"SCF converged: {bool(record.get('scf_converged'))}")
    print(f"Ionic converged: {bool(record.get('ionic_converged'))}")
    if record.get("missing_inputs"):
        print("Missing inputs: " + ", ".join(record["missing_inputs"]))
    if record.get("warnings"):
        print("Warnings: " + "; ".join(record["warnings"]))


if __name__ == "__main__":
    main()
