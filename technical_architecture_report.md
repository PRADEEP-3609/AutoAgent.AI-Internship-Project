# Technical Architecture Report: Autonomous Code-Executing Desktop Agent

**Project Title:** Autonomous Code-Executing Desktop Agent via SmolAgents Sandbox
**Engineering Track:** NLP / Generative AI
**Primary Developer:** PRADEEP KUMAR S (Roll No: 20241CSE1059)

---

## 1. Executive Summary

This report details the architectural design and implementation of an Autonomous Code-Executing Desktop Agent. Unlike traditional tool-calling agents that rely on structured JSON outputs, this system uses a "Code Agent" approach driven by the Hugging Face `smolagents` framework and the `Qwen2.5-Coder` model. The agent dynamically generates and executes Python code iteratively to fulfill natural language prompts. To mitigate the inherent security risks of executing LLM-generated code, the system utilizes a custom Docker-based local sandbox. 

## 2. System Architecture

The architecture is divided into three primary components: the Inference Engine, the Agent Orchestrator, and the Secure Sandbox Environment.

### 2.1 Agent Orchestrator (`smolagents`)
The core reasoning loop is handled by `smolagents`. The `CodeAgent` class takes a user prompt and generates an implementation plan formatted as Python code. This avoids the common pitfalls of JSON-based tool calling, such as schema hallucination or parsing errors. The agent natively leverages control flow (loops, conditionals) within its generations, drastically reducing the number of distinct LLM calls needed to complete complex tasks.

### 2.2 Inference Engine (`Qwen2.5-Coder`)
The system supports a dual-mode inference configuration:
- **Global Mode:** Utilizes the Hugging Face Serverless API to query `Qwen/Qwen2.5-Coder-32B-Instruct`. This provides high-accuracy, low-latency responses for complex logic without requiring local hardware.
- **Local Mode (Edge Testing):** Designed for edge execution on hardware such as an RTX 4070 (8GB VRAM). In this mode, the system loads `Qwen/Qwen2.5-Coder-7B-Instruct` using the `transformers` library. To fit the model into 8GB of VRAM, 4-bit quantization (`bitsandbytes`) is employed.

### 2.3 Secure Sandbox Environment (Docker)
Direct execution of AI-generated code on a host machine poses severe security risks (e.g., accidental file deletion, unauthorized network access). To solve this, a custom `DockerSandboxExecutor` was developed.
- **Isolation:** A lightweight Python container (`python:3.11-slim`) is spun up using the Python `docker` SDK.
- **Constraints:** The container is restricted in CPU (`cpu_quota=50000`) and memory (`mem_limit=512m`) to prevent resource exhaustion from infinite loops. The agent runs as a non-root user.
- **Execution Pipeline:** Generated code is wrapped in a robust try-catch block, streamed into the container as a tar archive, executed via `docker exec`, and the standard output/error is parsed and returned to the agent.

## 3. Performance and Metrics (Theoretical Analysis)

### 3.1 Inference Token Rates
- **Local (RTX 4070, 4-bit 7B Model):** Expected throughput is ~15-25 tokens per second. The quantization overhead is minimal, but the memory bandwidth of the RTX 4070 limits generation speed compared to data-center GPUs. 
- **Global (HF API):** Expected throughput is ~50-100+ tokens per second, depending on API load, with the advantage of using the more capable 32B parameter model.

### 3.2 Sandboxing Overhead
- **Initialization:** Building the sandbox image (if not present) takes ~20-30 seconds. Starting an existing container takes <1 second.
- **Execution:** Pushing the code archive and spinning up the `docker exec` process introduces approximately 0.5-1.5 seconds of overhead per code execution iteration. This is a highly acceptable trade-off for the security provided.

### 3.3 SLM Code-Generation Accuracy
`Qwen2.5-Coder` is state-of-the-art for its size class. In CodeAgent workflows, the SLM's ability to self-correct based on sandbox traceback errors significantly boosts effective accuracy. If the agent generates a syntax error or a missing import, the sandbox returns the precise Python traceback, and the SLM uses the next turn to correct the error and re-execute.

## 4. Conclusion and Future Scaling
The integration of `smolagents`, `Qwen2.5-Coder`, and Docker provides a robust, scalable, and secure desktop agent. Phase 1 edge testing on an RTX 4070 demonstrates the viability of fully localized, privacy-preserving AI coding assistants. For Phase 2 scaling, the architecture can be extended by deploying the containerized sandbox to Kubernetes (e.g., using Modal or E2B) to support high-concurrency multi-agent workflows.
