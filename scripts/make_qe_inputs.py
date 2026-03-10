#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from dft_job_utils import format_scheduler_script, parse_mesh, parse_modules, write_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a conservative QE workflow skeleton.")
    parser.add_argument("directory", help="Output directory for the workflow.")
    parser.add_argument("--task", choices=["scf", "relax", "dos", "band", "projwfc"], required=True)
    parser.add_argument("--prefix", default="qe_calc")
    parser.add_argument("--material", choices=["metal", "semiconductor", "insulator"], default="semiconductor")
    parser.add_argument("--pseudo-dir", default="./pseudo")
    parser.add_argument("--outdir", default="./tmp")
    parser.add_argument("--ecutwfc", type=float, default=60.0)
    parser.add_argument("--ecutrho", type=float)
    parser.add_argument("--conv-thr", type=float, default=1e-8)
    parser.add_argument("--mixing-beta", type=float, default=0.30)
    parser.add_argument("--forc-conv-thr", type=float, default=1e-3)
    parser.add_argument("--kmesh", default="6 6 6 0 0 0")
    parser.add_argument("--dense-kmesh", help="Denser mesh for NSCF in DOS workflows.")
    parser.add_argument("--species", help="Semicolon-separated entries like 'Si:28.0855:Si.UPF;O:15.999:O.UPF'")
    parser.add_argument("--structure-snippet", help="File containing CELL_PARAMETERS and ATOMIC_POSITIONS blocks.")
    parser.add_argument("--nbnd", type=int, help="Optional number of bands for NSCF or band workflows.")
    parser.add_argument("--scheduler", choices=["none", "slurm", "pbs"], default="slurm")
    parser.add_argument("--job-name", default="qe-job")
    parser.add_argument("--pw-command", default="pw.x -in INPUT")
    parser.add_argument("--dos-command", default="dos.x -in dos.in")
    parser.add_argument("--projwfc-command", default="projwfc.x -in projwfc.in")
    parser.add_argument("--bands-command", default="bands.x -in bands_pp.in")
    parser.add_argument("--modules", help="Comma-separated module names to leave in comments.")
    parser.add_argument("--time", default="24:00:00")
    parser.add_argument("--nodes", type=int, default=1)
    parser.add_argument("--ntasks-per-node", type=int, default=32)
    parser.add_argument("--cpus-per-task", type=int, default=1)
    parser.add_argument("--partition")
    parser.add_argument("--account")
    return parser.parse_args()


def parse_species(raw: str | None) -> list[tuple[str, float, str]]:
    if not raw:
        return [("X", 0.0, "X.UPF")]
    entries: list[tuple[str, float, str]] = []
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = [piece.strip() for piece in item.split(":")]
        if len(parts) != 3:
            raise ValueError(f"Invalid species entry: {item!r}")
        entries.append((parts[0], float(parts[1]), parts[2]))
    return entries or [("X", 0.0, "X.UPF")]


def occupations_block(material: str) -> list[str]:
    if material == "metal":
        return [
            "  occupations = 'smearing',",
            "  smearing = 'mv',",
            "  degauss = 0.020,",
        ]
    return ["  occupations = 'fixed',"]


def structure_block(species: list[tuple[str, float, str]], structure_snippet: str | None) -> str:
    species_lines = ["ATOMIC_SPECIES"]
    for label, mass, pseudo in species:
        species_lines.append(f"{label} {mass:.6f} {pseudo}")
    if structure_snippet:
        return "\n".join(species_lines + ["", Path(structure_snippet).read_text().rstrip()])
    first = species[0][0]
    placeholder = [
        "CELL_PARAMETERS angstrom",
        "1.000000 0.000000 0.000000",
        "0.000000 1.000000 0.000000",
        "0.000000 0.000000 1.000000",
        "",
        "ATOMIC_POSITIONS crystal",
        f"{first} 0.000000 0.000000 0.000000",
    ]
    return "\n".join(species_lines + [""] + placeholder)


def render_pw_input(
    *,
    calculation: str,
    prefix: str,
    pseudo_dir: str,
    outdir: str,
    ecutwfc: float,
    ecutrho: float,
    conv_thr: float,
    mixing_beta: float,
    forc_conv_thr: float,
    material: str,
    species: list[tuple[str, float, str]],
    structure_text: str,
    kmesh: list[int],
    nbnd: int | None = None,
) -> str:
    nat = 0
    in_atomic_positions = False
    for raw_line in structure_text.splitlines():
        line = raw_line.strip()
        upper = line.upper()
        if upper.startswith("ATOMIC_POSITIONS"):
            in_atomic_positions = True
            continue
        if in_atomic_positions:
            if not line:
                break
            if upper.startswith(("K_POINTS", "CELL_PARAMETERS", "ATOMIC_SPECIES")):
                break
            nat += 1
    nat = max(1, nat)
    ntyp = max(1, len(species))
    system_lines = [
        f"  ibrav = 0,",
        f"  nat = {nat},",
        f"  ntyp = {ntyp},",
        f"  ecutwfc = {ecutwfc:.3f},",
        f"  ecutrho = {ecutrho:.3f},",
        *occupations_block(material),
    ]
    if nbnd:
        system_lines.append(f"  nbnd = {nbnd},")
    blocks = [
        "&CONTROL",
        f"  calculation = '{calculation}',",
        f"  prefix = '{prefix}',",
        f"  pseudo_dir = '{pseudo_dir}',",
        f"  outdir = '{outdir}',",
        "  tstress = .true.,",
        "  tprnfor = .true.,",
        "/",
        "&SYSTEM",
        *system_lines,
        "/",
        "&ELECTRONS",
        f"  conv_thr = {conv_thr:.3e},",
        f"  mixing_beta = {mixing_beta:.2f},",
        "/",
    ]
    if calculation == "relax":
        blocks.extend(["&IONS", f"  forc_conv_thr = {forc_conv_thr:.3e},", "/"])
    blocks.extend(
        [
            structure_text,
            "",
            "K_POINTS automatic",
            f"{kmesh[0]} {kmesh[1]} {kmesh[2]} {kmesh[3]} {kmesh[4]} {kmesh[5]}",
        ]
    )
    return "\n".join(blocks)


def write_scheduler(
    directory: Path,
    filename: str,
    scheduler: str,
    job_name: str,
    command: str,
    modules: list[str],
    args: argparse.Namespace,
) -> None:
    if scheduler == "none":
        return
    extension = "slurm" if scheduler == "slurm" else "pbs"
    script = format_scheduler_script(
        scheduler,
        job_name,
        command,
        stdout_name=f"{job_name}.stdout",
        stderr_name=f"{job_name}.stderr",
        modules=modules,
        time_limit=args.time,
        nodes=args.nodes,
        ntasks_per_node=args.ntasks_per_node,
        cpus_per_task=args.cpus_per_task,
        partition=args.partition,
        account=args.account,
    )
    write_text(directory / f"{filename}.{extension}", script)


def write_workflow_plan(root: Path, task: str, notes: list[str], stages: list[dict[str, object]]) -> None:
    lines = ["# Workflow Plan", "", f"- Task: `{task}`", "", "## Stages", ""]
    for stage in stages:
        lines.extend(
            [
                f"### {stage['name']}",
                f"- Directory: `{stage['directory']}`",
                f"- Purpose: {stage['purpose']}",
                f"- Depends on: {stage['depends_on']}",
                f"- Files: {', '.join(stage['files'])}",
                "",
            ]
        )
    lines.extend(["## Notes", ""])
    lines.extend(f"- {note}" for note in notes)
    write_text(root / "WORKFLOW_PLAN.md", "\n".join(lines))


def main() -> None:
    args = parse_args()
    root = Path(args.directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    species = parse_species(args.species)
    structure_text = structure_block(species, args.structure_snippet)
    modules = parse_modules(args.modules)
    kmesh = parse_mesh(args.kmesh, 6)
    dense_kmesh = parse_mesh(args.dense_kmesh, 6) if args.dense_kmesh else kmesh
    ecutrho = args.ecutrho if args.ecutrho is not None else args.ecutwfc * 8.0
    notes = [
        f"Task: {args.task}",
        f"Material class assumption: {args.material}",
        f"Pseudo dir: {args.pseudo_dir}",
    ]
    if not args.structure_snippet:
        notes.append("The generated input contains placeholder CELL_PARAMETERS and ATOMIC_POSITIONS blocks.")
    stages: list[dict[str, object]] = []

    if args.task in {"scf", "relax"}:
        input_name = f"{args.task}.in"
        calc = "scf" if args.task == "scf" else "relax"
        write_text(
            root / input_name,
            render_pw_input(
                calculation=calc,
                prefix=args.prefix,
                pseudo_dir=args.pseudo_dir,
                outdir=args.outdir,
                ecutwfc=args.ecutwfc,
                ecutrho=ecutrho,
                conv_thr=args.conv_thr,
                mixing_beta=args.mixing_beta,
                forc_conv_thr=args.forc_conv_thr,
                material=args.material,
                species=species,
                structure_text=structure_text,
                kmesh=kmesh,
                nbnd=args.nbnd,
            ),
        )
        write_scheduler(root, "run", args.scheduler, args.job_name, args.pw_command.replace("INPUT", input_name), modules, args)
        stages.append(
            {
                "name": args.task.upper(),
                "directory": ".",
                "purpose": "Run the requested single-stage QE calculation.",
                "depends_on": "Validated pseudopotentials and structure",
                "files": [input_name, "run.<scheduler>"],
            }
        )

    elif args.task == "dos":
        scf_dir = root / "01-scf"
        nscf_dir = root / "02-nscf"
        dos_dir = root / "03-dos"
        write_text(
            scf_dir / "scf.in",
            render_pw_input(
                calculation="scf",
                prefix=args.prefix,
                pseudo_dir=args.pseudo_dir,
                outdir=args.outdir,
                ecutwfc=args.ecutwfc,
                ecutrho=ecutrho,
                conv_thr=args.conv_thr,
                mixing_beta=args.mixing_beta,
                forc_conv_thr=args.forc_conv_thr,
                material=args.material,
                species=species,
                structure_text=structure_text,
                kmesh=kmesh,
            ),
        )
        write_text(
            nscf_dir / "nscf.in",
            render_pw_input(
                calculation="nscf",
                prefix=args.prefix,
                pseudo_dir=args.pseudo_dir,
                outdir=args.outdir,
                ecutwfc=args.ecutwfc,
                ecutrho=ecutrho,
                conv_thr=args.conv_thr,
                mixing_beta=args.mixing_beta,
                forc_conv_thr=args.forc_conv_thr,
                material=args.material,
                species=species,
                structure_text=structure_text,
                kmesh=dense_kmesh,
                nbnd=args.nbnd,
            ),
        )
        write_text(
            dos_dir / "dos.in",
            "\n".join(
                [
                    "&DOS",
                    f"  prefix = '{args.prefix}',",
                    f"  outdir = '{args.outdir}',",
                    "  fildos = 'dos.dat',",
                    "/",
                ]
            ),
        )
        write_scheduler(scf_dir, "run", args.scheduler, f"{args.job_name}-scf", args.pw_command.replace("INPUT", "scf.in"), modules, args)
        write_scheduler(nscf_dir, "run", args.scheduler, f"{args.job_name}-nscf", args.pw_command.replace("INPUT", "nscf.in"), modules, args)
        write_scheduler(dos_dir, "run", args.scheduler, f"{args.job_name}-dos", args.dos_command, modules, args)
        notes.extend(
            [
                "Run 01-scf before 02-nscf and keep prefix, pseudo_dir, and outdir identical across stages.",
                "Increase --dense-kmesh if the DOS is still undersampled.",
            ]
        )
        stages.extend(
            [
                {
                    "name": "SCF",
                    "directory": "01-scf",
                    "purpose": "Generate a converged parent charge density.",
                    "depends_on": "Validated pseudopotentials and structure",
                    "files": ["scf.in", "run.<scheduler>"],
                },
                {
                    "name": "NSCF",
                    "directory": "02-nscf",
                    "purpose": "Sample a denser k-mesh using the parent prefix and outdir.",
                    "depends_on": "Consistent prefix and outdir from 01-scf",
                    "files": ["nscf.in", "run.<scheduler>"],
                },
                {
                    "name": "DOS",
                    "directory": "03-dos",
                    "purpose": "Post-process the NSCF result with dos.x.",
                    "depends_on": "QE scratch data from 01-scf and 02-nscf",
                    "files": ["dos.in", "run.<scheduler>"],
                },
            ]
        )

    elif args.task == "band":
        scf_dir = root / "01-scf"
        bands_dir = root / "02-bands"
        post_dir = root / "03-post"
        write_text(
            scf_dir / "scf.in",
            render_pw_input(
                calculation="scf",
                prefix=args.prefix,
                pseudo_dir=args.pseudo_dir,
                outdir=args.outdir,
                ecutwfc=args.ecutwfc,
                ecutrho=ecutrho,
                conv_thr=args.conv_thr,
                mixing_beta=args.mixing_beta,
                forc_conv_thr=args.forc_conv_thr,
                material=args.material,
                species=species,
                structure_text=structure_text,
                kmesh=kmesh,
            ),
        )
        bands_template = render_pw_input(
            calculation="bands",
            prefix=args.prefix,
            pseudo_dir=args.pseudo_dir,
            outdir=args.outdir,
            ecutwfc=args.ecutwfc,
            ecutrho=ecutrho,
            conv_thr=args.conv_thr,
            mixing_beta=args.mixing_beta,
            forc_conv_thr=args.forc_conv_thr,
            material=args.material,
            species=species,
            structure_text=structure_text,
            kmesh=kmesh,
            nbnd=args.nbnd,
        )
        bands_template = bands_template.rsplit("K_POINTS automatic", 1)[0].rstrip() + "\n\n" + "\n".join(
            [
                "K_POINTS crystal_b",
                "# Replace with a real path from SeeK-path or literature before running.",
                "# Example format only:",
                "# 4",
                "# 0.0 0.0 0.0 20 ! G",
                "# 0.5 0.0 0.0 20 ! X",
            ]
        )
        write_text(bands_dir / "bands.in.template", bands_template)
        write_text(
            post_dir / "bands_pp.in",
            "\n".join(
                [
                    "&BANDS",
                    f"  prefix = '{args.prefix}',",
                    f"  outdir = '{args.outdir}',",
                    "  filband = 'bands.dat',",
                    "/",
                ]
            ),
        )
        write_scheduler(scf_dir, "run", args.scheduler, f"{args.job_name}-scf", args.pw_command.replace("INPUT", "scf.in"), modules, args)
        write_scheduler(post_dir, "run", args.scheduler, f"{args.job_name}-post", args.bands_command, modules, args)
        notes.extend(
            [
                "Replace 02-bands/bands.in.template with a real K_POINTS crystal_b path before generating the band step run script.",
                "Run 01-scf first, then create 02-bands/bands.in from the template, then run 03-post with bands.x.",
            ]
        )
        stages.extend(
            [
                {
                    "name": "SCF",
                    "directory": "01-scf",
                    "purpose": "Generate a converged parent charge density.",
                    "depends_on": "Validated pseudopotentials and structure",
                    "files": ["scf.in", "run.<scheduler>"],
                },
                {
                    "name": "Bands",
                    "directory": "02-bands",
                    "purpose": "Run the path calculation with a finalized crystal_b path.",
                    "depends_on": "SCF scratch data and a replaced bands.in.template",
                    "files": ["bands.in.template"],
                },
                {
                    "name": "bands.x",
                    "directory": "03-post",
                    "purpose": "Post-process the bands calculation for plotting.",
                    "depends_on": "Completed 02-bands run and consistent prefix/outdir",
                    "files": ["bands_pp.in", "run.<scheduler>"],
                },
            ]
        )

    elif args.task == "projwfc":
        scf_dir = root / "01-scf"
        nscf_dir = root / "02-nscf"
        proj_dir = root / "03-projwfc"
        write_text(
            scf_dir / "scf.in",
            render_pw_input(
                calculation="scf",
                prefix=args.prefix,
                pseudo_dir=args.pseudo_dir,
                outdir=args.outdir,
                ecutwfc=args.ecutwfc,
                ecutrho=ecutrho,
                conv_thr=args.conv_thr,
                mixing_beta=args.mixing_beta,
                forc_conv_thr=args.forc_conv_thr,
                material=args.material,
                species=species,
                structure_text=structure_text,
                kmesh=kmesh,
            ),
        )
        write_text(
            nscf_dir / "nscf.in",
            render_pw_input(
                calculation="nscf",
                prefix=args.prefix,
                pseudo_dir=args.pseudo_dir,
                outdir=args.outdir,
                ecutwfc=args.ecutwfc,
                ecutrho=ecutrho,
                conv_thr=args.conv_thr,
                mixing_beta=args.mixing_beta,
                forc_conv_thr=args.forc_conv_thr,
                material=args.material,
                species=species,
                structure_text=structure_text,
                kmesh=dense_kmesh,
                nbnd=args.nbnd,
            ),
        )
        write_text(
            proj_dir / "projwfc.in",
            "\n".join(
                [
                    "&PROJWFC",
                    f"  prefix = '{args.prefix}',",
                    f"  outdir = '{args.outdir}',",
                    "  DeltaE = 0.01,",
                    "  filpdos = 'projdos.dat',",
                    "/",
                ]
            ),
        )
        write_scheduler(scf_dir, "run", args.scheduler, f"{args.job_name}-scf", args.pw_command.replace("INPUT", "scf.in"), modules, args)
        write_scheduler(nscf_dir, "run", args.scheduler, f"{args.job_name}-nscf", args.pw_command.replace("INPUT", "nscf.in"), modules, args)
        write_scheduler(proj_dir, "run", args.scheduler, f"{args.job_name}-projwfc", args.projwfc_command, modules, args)
        notes.extend(
            [
                "Run 01-scf before 02-nscf, then launch 03-projwfc using the same prefix and outdir.",
                "Increase --dense-kmesh if the projected DOS remains undersampled.",
            ]
        )
        stages.extend(
            [
                {
                    "name": "SCF",
                    "directory": "01-scf",
                    "purpose": "Generate a converged parent charge density.",
                    "depends_on": "Validated pseudopotentials and structure",
                    "files": ["scf.in", "run.<scheduler>"],
                },
                {
                    "name": "NSCF",
                    "directory": "02-nscf",
                    "purpose": "Increase the sampling for orbital projection analysis.",
                    "depends_on": "Consistent prefix and outdir from 01-scf",
                    "files": ["nscf.in", "run.<scheduler>"],
                },
                {
                    "name": "projwfc.x",
                    "directory": "03-projwfc",
                    "purpose": "Compute projected DOS or orbital projections from the NSCF data.",
                    "depends_on": "QE scratch data from 01-scf and 02-nscf",
                    "files": ["projwfc.in", "run.<scheduler>"],
                },
            ]
        )

    write_text(root / "README.next-steps", "\n".join(f"- {line}" for line in notes))
    write_workflow_plan(root, args.task, notes, stages)


if __name__ == "__main__":
    main()
