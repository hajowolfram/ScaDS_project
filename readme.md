## Getting Started

Follow these steps to set up and run the project:

### 1. Install Dependencies

First, install all the required Python packages specified in `requirements.txt`. You can do this using `pip`:

```bash
pip install -r requirements.txt
```

### 2. Set Root Directory Path in .env

Ensure you have a .env file in the root of your project. You can use this file to set the necessary environment variables.

```bash
SUMO_PROJECT_PATH=your_path_to_root_directory
```

### 3. Install gymnasium package locally in project root directory

```bash
pip install -e .
```

### 4. Install SUMO (traffic simulation software) [here](https://sumo.dlr.de/docs/Installing/index.html)

### Citations:

This project utilizes components from the RL Dresden Algorithm Suite. If you use this code in your own projects or papers, please cite it as follows:

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