## Overview

This project provides a framework to train different types of autonomous vehicle RL agents 
via SUMO simulations to improve traffic flow. The provided SUMO network and configuration files allow for basic training of vehicle controller agents in a simulation environment with IDM vehicles. SUMO also supports OSM, and this project will likely be extended to support traffic controller agents in addition to autonomous vehicle controllers in the future.

## Important

While some basic simulation functionality has been implemented, this project is still a work in progress.

## Setup Guide

Follow these steps to set up and run the project:

### 1. Install Dependencies

Install all required Python packages specified in `requirements.txt`. You can do this using `pip`:

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Ensure you set the path of the root directory in a `.env` file:

```bash
SUMO_PROJECT_PATH=your_path_to_root_directory
```

### 3. Install Package Locally

Install gymnasium package locally in project root directory with `pip`:

```bash
pip install -e .
```

### 4. Install SUMO 

Install `SUMO` (simulation of urban mobility) [here](https://sumo.dlr.de/docs/Installing/index.html)

### 5. run with main.py (NOTE FUNCTIONALITY STILL W.I.P) 

```bash
python3 ./main.py
```

## Further Use:

In order to add custom environments, please refer to the gymnasium documentation [here](https://www.gymlibrary.dev/content/environment_creation/).
It is reccomended to utilise gymnasium to ensure compatability with gymnasium's provided RL modules.
Support for different agents coming soon!

## Citations:

This project utilizes [SUMO](https://sumo.dlr.de/docs/index.html) (simulation of urban mobility)

```bash
@inproceedings{dlr127994,
  title = {Microscopic Traffic Simulation using SUMO},
  month = {November},
  author = {Alvarez Lopez, Pablo and Behrisch, Michael and Bieker-Walz, Laura and Erdmann, Jakob and Fl{\"o}tter{\"o}d, Yun-Pang and Hilbrich, Robert and L{\"u}cken, Leonhard and Rummel, Johannes and Wagner, Peter and Wie{\ss}ner, Evamarie},
  pages = {2575--2582},
  year = {2018},
  booktitle = {2019 IEEE Intelligent Transportation Systems Conference (ITSC)},
  publisher = {IEEE},
  keywords = {traffic simulation, modelling, optimization},
  url = {https://elib.dlr.de/127994/},
  abstract = {Microscopic traffic simulation is an invaluable tool for traffic research. In recent years, both the scope of research and the capabilities of the tools have been extended considerably. This article presents the latest developments concerning intermodal traffic solutions, simulator coupling and model development and validation on the example of the open source traffic simulator SUMO.}
}
```

This project utilizes components from the RL Dresden Algorithm Suite.

```bash
@misc{TUDRL,
  author = {Waltz, Martin and Paulig, Niklas},
  title = {RL Dresden Algorithm Suite},
  year = {2022},
  publisher = {GitHub},
  journal = {GitHub Repository},
  howpublished = {\url{https://github.com/MarWaltz/TUD_RL}}
}
```