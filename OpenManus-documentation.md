```markdown
# OpenManus: An Open-Source Framework for Building General AI Agents

[![GitHub stars](https://img.shields.io/github/stars/mannaandpoem/OpenManus?style=social)](https://github.com/mannaandpoem/OpenManus/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord Follow](https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat)](https://discord.gg/DYn29wFk9z)

## What is OpenManus?

OpenManus is an open-source project designed to facilitate the creation of versatile AI agents capable of performing a wide range of tasks using multiple tools.  It's inspired by Manus but aims to be fully open and accessible, requiring no invite codes.  The project was initiated by members of the MetaGPT community and emphasizes rapid iteration and community contributions. OpenManus leverages Large Language Models (LLMs) to power its agents, enabling them to interact with the real world through tools like web browsing.

Key features:

*   **Open and Accessible:** No invite codes or restrictions.
*   **Rapid Development:**  The initial prototype was developed in just 3 hours.
*   **Community-Driven:**  Open to contributions and feedback.
*   **LLM-Powered:**  Utilizes LLMs for intelligent decision-making and interaction.
*   **Multi-Tool Support:** Agents can use various tools to accomplish tasks.
*   **Easy to Use:** Simple setup and configuration.

## Quick Start

This section guides you through installing and running a basic OpenManus agent.

### Installation

There are two primary methods for installing OpenManus: using `conda` or `uv`.  `uv` is recommended for its speed and improved dependency management.

#### Method 1: Using conda (Traditional)

1.  **Create a Conda Environment:**

    ```bash
    conda create -n open_manus python=3.12
    conda activate open_manus
    ```

2.  **Clone the Repository:**

    ```bash
    git clone https://github.com/mannaandpoem/OpenManus.git
    cd OpenManus
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

#### Method 2: Using uv (Recommended)

1.  **Install `uv`:**

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Clone the Repository:**

    ```bash
    git clone https://github.com/mannaandpoem/OpenManus.git
    cd OpenManus
    ```

3.  **Create and Activate a Virtual Environment:**

    ```bash
    uv venv
    source .venv/bin/activate  # On Unix/macOS
    # Or on Windows:
    # .venv\Scripts\activate
    ```

4.  **Install Dependencies:**

    ```bash
    uv pip install -r requirements.txt
    ```

### Basic Usage

1.  **Configuration:**

    Before running OpenManus, you need to configure your LLM API keys.

    *   Create a `config.toml` file in the `config` directory:

        ```bash
        cp config/config.example.toml config/config.toml
        ```

    *   Edit `config/config.toml` and replace the placeholder API keys with your actual keys:

        ```toml
        # Global LLM configuration
        [llm]
        model = "gpt-4o"
        base_url = "https://api.openai.com/v1"
        api_key = "sk-..."  # Replace with your actual API key
        max_tokens = 4096
        temperature = 0.0

        # Optional configuration for specific LLM models (e.g., for vision)
        [llm.vision]
        model = "gpt-4o"
        base_url = "https://api.openai.com/v1"
        api_key = "sk-..."  # Replace with your actual API key
        ```
        You can specify the model, base URL, API key, maximum tokens, and temperature. The `[llm.vision]` section allows for separate configuration of vision-specific models, if needed.

2.  **Run OpenManus:**

    Execute the following command in your terminal:

    ```bash
    python main.py
    ```

    This will start the OpenManus agent.  You can then interact with it by providing input through the terminal.

3.  **Unstable Version (Development Branch):**

    To try out the latest development features, you can run:

    ```bash
    python run_flow.py
    ```

## Dependencies and Requirements

OpenManus relies on several Python packages.  These are listed in `requirements.txt` and are automatically installed when using `pip` or `uv`.

Key dependencies include:

*   **pydantic:** For data validation and settings management.
*   **openai:**  For interacting with OpenAI's LLMs.
*   **tenacity:** For adding retry logic to function calls.
*   **loguru:** For logging.
*   **browser-use:** A library based on playwright, for web interaction.
*   **googlesearch-python:** For performing Google searches.
*   **playwright:** For browser automation.

**Python Version:** OpenManus requires Python 3.12 or higher.

## Project Structure Overview

The repository has the following structure (based on the provided directory listing):

*   **CODE_OF_CONDUCT.md:**  Outlines the expected behavior for contributors.
*   **README.md / README_zh.md:**  Project documentation in English and Chinese.
*   **requirements.txt:** Lists the project's Python dependencies.
*   **setup.py:**  Python packaging configuration.
*   **config/** (Not included in packed file, but mentioned in README): Contains configuration files, including `config.example.toml` and `config.toml`.
* **main.py** (Not included in packed file): The main entry point for the stable version.
* **run_flow.py**(Not included in packed file): The entry point for the development version.
*   **assets/** (Not included in packed file, but mentioned in README): Contains images used in the README, such as the community group QR code.

## Contributing Guidelines

OpenManus welcomes contributions!  You can contribute by:

*   Creating issues to report bugs or suggest new features.
*   Submitting pull requests with code changes or improvements.
*   Contacting the maintainer, Xinbin Liang (@mannaandpoem), via email: mannaandpoem@gmail.com.

Please refer to the `CODE_OF_CONDUCT.md` for guidelines on community interaction and expected behavior.

## Advanced Usage Examples

The provided file does not include specific code examples beyond the basic `main.py` and `run_flow.py` execution.  However, the README mentions that the project is based on concepts from `anthropic-computer-use` and `browser-use`.  Users interested in advanced usage should explore those projects for inspiration and to understand the underlying mechanisms for web interaction and agent control.

## Package Summary & Installation (setup.py)

The `setup.py` file indicates that OpenManus is packaged as a Python package named "openmanus" with version 0.1.0.  It can be installed using `pip`:

```bash
pip install openmanus
```
However, since the package is not yet published to PyPI, this command will not work. The installation instructions provided earlier (cloning the repository and installing dependencies) are the correct way to install the project currently.

The `setup.py` also specifies an entry point:

```
    entry_points={
        "console_scripts": [
            "openmanus=main:main",
        ],
    },
```
This means that after installation (if it were published to PyPI), you could run the agent from the command line using the command `openmanus`. This would execute the `main` function within the `main.py` file. There are no public APIs documented in this file.
```
