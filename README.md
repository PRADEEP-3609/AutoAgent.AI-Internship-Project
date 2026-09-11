# AutoAgent.AI: Secure Autonomous Desktop Automation using Qwen 2.5

This repository contains the implementation of a "Code Agent" utilizing the Hugging Face `smolagents` framework, driven by the open-weights `Qwen2.5-Coder` model. The agent writes and executes Python code iteratively to solve user intents. To ensure security, all code execution is performed inside a locally managed Docker sandbox environment.

## Features
- **CodeAgent Architecture:** Uses `smolagents` CodeAgent paradigm to naturally write Python scripts (loops, conditionals, etc.) instead of rigid JSON tool-calling.
- **Local / Global Toggle:** Seamlessly switch between local edge execution (e.g., RTX 4070 via `transformers`) and global API execution.
- **Docker Sandboxing:** Includes a custom `DockerSandboxExecutor` that strictly isolates the agent runtime, protecting your host machine from unintended side effects.

## Prerequisites
- **Python 3.10+**
- **Docker Desktop** (or Docker Engine) running on your local machine.
- **Hugging Face Token** (for global mode, or for downloading gated models in local mode).

## Installation

1. Clone or navigate to this repository.
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables by creating a `.env` file:
   ```env
   HF_TOKEN="Enter your hugging face token here"
   ```

## Usage (Web UI)
You can run the agent through a user-friendly Streamlit web application. This is the recommended way to use the agent.
```bash
pip install streamlit ansi2html
python -m streamlit run app.py
```

### Global Mode (Default)
This mode uses the Hugging Face Serverless API. It is fast and requires no local GPU resources.
```bash
python agent.py --mode global --prompt "Write a python script to calculate the first 10 Fibonacci numbers and print them."
```

### Local Mode (Edge Execution)
This mode downloads the model and runs it on your local GPU (e.g., RTX 4070). The script defaults to `Qwen/Qwen2.5-Coder-3B-Instruct` in bfloat16, providing a great balance between intelligence and fast execution without overloading your VRAM.
```bash
python agent.py --mode local --prompt "Write a python script to calculate the first 10 Fibonacci numbers and print them."
```

## How It Works

1. **Initialization:** The script loads the chosen LLM (either via `HfApiModel` or `TransformersModel`).
2. **Sandbox Setup:** The `DockerSandboxExecutor` checks if the sandbox image exists. If not, it builds it from `Dockerfile.sandbox`. It then starts a detached container.
3. **Execution Loop:** The user prompt is passed to the `smolagents.CodeAgent`. The agent generates a Python script to solve the task.
4. **Sandboxed Code Run:** Instead of running the code locally, the agent passes the code to the `DockerSandboxExecutor`, which injects it into the container and runs it.
5. **Feedback Loop:** If the code fails or produces an error, the agent receives the traceback, fixes the code, and tries again.
6. **Teardown:** Once the task is complete, the sandbox container is safely stopped and removed.

## Troubleshooting

- **Docker Errors:** Ensure Docker Desktop is running. If you get permission errors, ensure your user is added to the `docker` group (Linux) or Docker is running with appropriate permissions.
- **Memory Errors in Local Mode:** If you run out of VRAM, ensure `bitsandbytes` is properly installed for 4-bit quantization (`load_in_4bit=True`).
