from __future__ import annotations

import datetime
import pathlib
import re
import subprocess
import sys
import typing

import click

if typing.TYPE_CHECKING:
    from typing import Sequence, Optional
    from datetime import datetime


class WallTimeParamType(click.ParamType):
    name = "walltime"

    def convert(self, value, param, ctx) -> str:
        pattern = re.compile(
            r"""
            ^                       # begin
            (?P<days>\d+)??         # optional days, non-greedy
            (-?(?P<hours>\d+):?)??  # optional hours, non-greedy
            (?P<minutes>\d+)?       # optional minutes, greedy
            (:(?P<seconds>\d+))?    # optional seconds, greedy
            $                       # end
            """,
            re.VERBOSE,
        )

        match = pattern.match(value)
        if match:
            return value
        else:
            self.fail(f"{value!r} is not a valid walltime", param, ctx)


@click.command()
@click.argument(
    "config",
    type=click.Path(exists=True, dir_okay=False),
)
@click.argument(
    "configs",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "-n",
    "--ncpus",
    type=click.IntRange(min=1, max=64),
    default=2,
    help="Number of CPUs.  [default: 2]",
)
@click.option(
    "-g",
    "--ngpus",
    type=click.IntRange(min=0, max=4),
    default=1,
    help="Number of GPUs.  [default: 1]",
)
@click.option(
    "-w",
    "--wall-time",
    type=WallTimeParamType(),
    default="12:00:00",
    help="Wall time.  [default: 12:00:00]",
)
@click.option(
    "--after",
    type=int,
    default=None,
    help="Start after specified job exited OK.",
)
@click.option(
    "--chain",
    "chain",
    flag_value="chain",
    default=False,
    help="Submit jobs as a dependency chain.",
)
@click.option(
    "--dry-run",
    "dry_run",
    flag_value="dry_run",
    default=False,
    help="Perform a dry run and do not submit.",
)
def main(
    config: click.Path,
    configs: Sequence[click.Path],
    *,
    ncpus: int,
    ngpus: int,
    wall_time: datetime,
    after: Optional[int],
    chain: bool,
    dry_run: bool,
):
    """Submit NAMD jobs specified by CONFIG."""

    configs = [config, *configs]

    _prep(
        configs,
        ncpus=ncpus,
        ngpus=ngpus,
        wall_time=wall_time,
    )

    if not dry_run:
        _submit(configs, after=after, chain=chain)


def _path_relative_to_root(path: pathlib.Path):
    """
    Walk up the file system and return the path relative to the next git root directory (including the name of the git
    directory) or return the path relative to home, whichever comes first.
    """
    path = path.absolute()
    home = path.home()
    for parent in path.parents:
        git = parent / ".git"
        if git.is_dir():
            return parent.name / path.relative_to(parent)
        if parent == home:
            return path.relative_to(parent)


def _jobname(path: pathlib.Path):
    """Determine the jobname."""
    relative = _path_relative_to_root(path)
    return "_".join(relative.parts)


def _prep(
    configs: Sequence[click.Path],
    *,
    ncpus: int,
    ngpus: int,
    wall_time: datetime,
):
    """Prepare all jobs."""

    # Write the submit script.
    for c in configs:
        path = pathlib.Path(c)
        with open(path.with_suffix(".slurm"), "w") as f:
            f.writelines(
                [
                    "#!/bin/bash\n",
                    "\n",
                    f"#SBATCH --job-name={_jobname(path)}\n",
                    f"#SBATCH --time={wall_time}\n",
                    "#SBATCH --nodes=1\n",
                    f"#SBATCH --ntasks-per-node={ncpus}\n",
                ]
            )
            if ngpus > 0:
                f.write(f"#SBATCH --gpus={ngpus}\n")
            f.writelines(["\n", "module purge\n", "module load namd3\n", "\n"])
            f.write(f"namd3 +p {ncpus} +setcpuaffinity")
            if ngpus > 0:
                f.write(" +devices ${CUDA_VISIBLE_DEVICES}")
            f.write(f" {path.name} > {path.stem + '.out'}\n")


def _submit(configs: Sequence[click.Path], *, after: Optional[int], chain: bool):
    """Submit all jobs."""
    for c in configs:
        path = pathlib.Path(c)
        cmdline = ["sbatch", str(path.with_suffix(".slurm"))]
        if after is not None:
            cmdline += [f"--dependency=afterok:{after}"]
        print("Running: " + " ".join(cmdline))
        try:
            stdout = subprocess.run(
                cmdline, check=True, capture_output=True, cwd=path.parent
            ).stdout.decode("utf-8")
            jobid = stdout.split()[-1]
            if chain:
                after = jobid
        except Exception as e:
            sys.exit(f"{e}")
