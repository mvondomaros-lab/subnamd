# subnamd

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-green.svg)](https://www.python.org/)
[![MIT license](https://img.shields.io/badge/License-MIT-green.svg)](https://lbesson.mit-license.org/)

Submit NAMD jobs. Public, but not intended for general use.

## Installation

1.  Setup the the [uv](https://docs.astral.sh/uv/) package manager.
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
    Add the following lines to your `uv.toml` (usually located under `~/.config/uv/uv.toml`).
    ```toml
    [[index]]
    name = "mvondomaros-lab"
    url = "https://mvondomaros-lab.github.io"
    ```
2.  Install `subnamd`.
    ```bash
    uv tool install subnamd
    ```

## Usage

Show a help message.

```bash
subnamd --help
```

Submit a NAMD job specified by `project/namd.conf`, with 2 CPUs, 1 GPU, and a wall time limit of 12 hours.

```bash
subnamd -n 2 -g 1 -w 12:00:00 project/namd.conf
```

Submit multiple NAMD jobs at once.

```bash
subnamd project1/namd.conf project2/namd.conf project3/namd.conf
```

Submit a NAMD job, but do not run until job '12345' has completed successfully.

```bash
subnamd --after 12345 namd.conf
```

Submit multiple NAMD jobs as a dependency chain, meaning the second job wil only run after the first one has
completed sucessfully, and so on.

```bash
subnamd --chain project1/namd.conf project2/namd.conf project3/namd.conf
```

