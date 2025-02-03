<!-- ABOUT THE PROJECT -->
<div align="center">
  <h3 align="center">Hitchmap</h3>
  <p align="center">
    The map to hitchhiking the world.
    <br />
    <br />
    <a href="https://github.com/othneildrew/Best-README-Template/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/othneildrew/Best-README-Template/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

## About The Project

Read more [here](https://hitchwiki.org/en/Hitchwiki:Maps).


### Fork and Divergence

This repository, [`Hitchwiki/hitchmap`](https://github.com/Hitchwiki/hitchmap), is a fork of [`bobjesvla/hitch`](https://github.com/bobjesvla/hitch). While both projects share a common origin, they have since taken different development paths. At this stage, it remains uncertain which repository will emerge as the mainline project. However, we remain open to collaboration and potential reconciliation of efforts in the future.

For contributors and users, we recommend reviewing both repositories to determine which best fits your needs.


## Getting Started

Set up Python virtual environment, install requirements and download the latest database dump:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
curl https://hitchmap.com/dump.sqlite > db/points.sqlite

OR

conda install folium==0.16.0 networkx==3.2.1
curl https://hitchmap.com/dump.sqlite > db/points.sqlite
```

Initialize and run the Flask server:

```bash
flask --app hitch generate-all
flask --app hitch generate-all
flask run
```

In order to run the project continuously, use `cron.sh` to set up corresponding cronjobs to update the views and `hitchmap.conf` as a basic NGINX configuration.

## Contributing

Contributions are greatly appreciated and we are happy to help you get started with your first feature or bug fix.

Join the conversation about a map for hitchhiking in our [Signal Chat](https://signal.group/#CjQKIDyYgIxcOUCEPYu8-JawC_tv1bcgkAhvbISRZkN45MMVEhCtydy3DOOCKEAE_tsR6g9s).

File an [issue](https://github.com/bopjesvla/hitch/issues) if you have a feature request or found a bug.

Perform a [pull request](https://github.com/bopjesvla/hitch/pulls) from your [fork](https://github.com/bopjesvla/hitch/fork) of the repository if you solved an issue. (It's best to file an issue first so we can discuss it and reference it in the PR.)

### Linting

We use Ruff for linting [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/). The settings can be found in `ruff.toml`.

To configure automatic linting for VS Code check out the extension [https://github.com/astral-sh/ruff-vscode](https://github.com/astral-sh/ruff-vscode).

## Data
If you find the data collected and provided by hitchmap.com helpful, feel free to cite it using:
```
@misc{hitchhiking,
author = {Bob de Ruiter, Till Wenke},
title = {Dataset of Hitchhiking Trips},
year = {2024},
url = {https://hitchmap.com},
}
```

## License

The software provided in this repository is licensed under AGPL 3.0. The Hitchmap database is licensed under the ODBL, the license used by OpenStreetMap.
