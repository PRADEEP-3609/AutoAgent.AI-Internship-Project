import os
from dotenv import load_dotenv

# Try importing smolagents and custom modules
try:
    from smolagents import CodeAgent, InferenceClientModel, TransformersModel, DuckDuckGoSearchTool
    from sandbox_executor import DockerSandboxExecutor
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you have installed the requirements: pip install -r requirements.txt")
    exit(1)

# Load environment variables from .env file
load_dotenv()

def create_agent(mode="global", model_id=None, authorized_dirs=None, use_docker=True):
    """
    Initializes the CodeAgent with either a local or global model,
    and optionally configures the Docker sandbox for code execution.
    """
    if authorized_dirs is None:
        authorized_dirs = [os.path.join(os.path.expanduser("~"), "Desktop")]

    if mode == "local":
        # Use transformers for local edge execution
        # Using the balanced 3B model for a good mix of speed and intelligence
        model_id = model_id or "Qwen/Qwen2.5-Coder-3B-Instruct"
        print(f"Initializing Local Model: {model_id} via transformers in 8-bit mode...")
        try:
            import transformers
            from transformers import BitsAndBytesConfig
            
            # Monkey-patch AutoModelForCausalLM to inject 8-bit quantization
            # This forces the model to fit perfectly into VRAM, preventing slow CPU offloads
            original_from_pretrained = transformers.AutoModelForCausalLM.from_pretrained
            
            def quant_from_pretrained(*args, **kwargs):
                kwargs['quantization_config'] = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_enable_fp32_cpu_offload=True
                )
                return original_from_pretrained(*args, **kwargs)
                
            transformers.AutoModelForCausalLM.from_pretrained = quant_from_pretrained
            
            try:
                model = TransformersModel(
                    model_id=model_id,
                    device_map="auto",
                    torch_dtype="float16"
                )
            finally:
                # Restore the original method immediately after initialization
                transformers.AutoModelForCausalLM.from_pretrained = original_from_pretrained
                
        except Exception as e:
            print(f"Failed to load local model. Did you install torch and bitsandbytes? Error: {e}")
            raise
    else:
        # Use Hugging Face Inference API for global execution
        model_id = model_id or "Qwen/Qwen2.5-Coder-32B-Instruct"
        print(f"Initializing Global Model: {model_id} via InferenceClientModel...")
        token = os.getenv("HF_TOKEN")
        if not token:
            print("WARNING: HF_TOKEN environment variable not set. Global mode may fail.")
        model = InferenceClientModel(
            model_id=model_id,
            token=token
        )

    # Initialize the custom Docker sandbox executor
    sandbox = None
    if use_docker:
        print("Initializing Docker Sandbox Environment...")
        sandbox = DockerSandboxExecutor(authorized_dirs=authorized_dirs)

    # Define a strong system prompt to prevent hallucinated functions
    if use_docker:
        sandbox_paths = [f"/home/agentuser/{os.path.basename(os.path.normpath(d))}" for d in authorized_dirs]
        paths_str = ", ".join(sandbox_paths)
        env_rule = f"Your code will be executed in a secure Docker sandbox. You ONLY have write access to these mounted directories: {paths_str}. DO NOT attempt to write to any other directories."
    else:
        env_rule = "Your code will be executed DIRECTLY on the user's real Windows host machine. Use native Windows file paths (e.g. C:\\\\Users\\\\...)."
        
    system_prompt = f"""You are an autonomous Python code execution agent.
You must write complete, self-contained Python scripts to solve the user's tasks.
CRITICAL RULES:
1. DO NOT assume the existence of magically injected functions (like `list_files`, `desktop_screenshots`, or `move_files`).
2. You must implement all logic using standard Python libraries.
3. **IMPORTANT**: You must explicitly `import` any libraries you use at the top of your code (e.g., `import os`, `import shutil`, `from datetime import datetime`).
4. {env_rule}
5. When interacting with files, ALWAYS perform highly flexible, case-insensitive searches. You MUST remove all spaces from both the search term and the filename (e.g., `target.replace(" ", "").lower() in filename.replace(" ", "").lower()`). This prevents failures when users omit extensions or add/remove spaces in their requests.
6. When you have completed the task, you must call the `final_answer(result)` function to terminate. The string you pass to `final_answer()` MUST accurately report the true outcome (e.g., if a file wasn't found, the final answer must explicitly state that it failed to find it, rather than blindly saying it was complete).
"""

    # Create the CodeAgent
    # We pass the standard authorized imports. The agent will write code that
    # is then run in our sandbox.
    # We also inject the DuckDuckGoSearchTool so the agent can browse the web.
    search_tool = DuckDuckGoSearchTool()
    
    agent = CodeAgent(
        tools=[search_tool], 
        model=model,
        additional_authorized_imports=["requests", "pandas", "numpy", "json", "os", "shutil", "math", "datetime", "sys", "time", "ntpath", "posixpath"]
    )
    
    # Overwrite the default LocalPythonInterpreter with our secure Docker executor
    # Depending on the smolagents version, we either replace python_executor or step logic
    if sandbox:
        agent.python_executor = sandbox

    # Append our custom rules to the agent's system prompt
    agent.prompt_templates["system_prompt"] += f"\n\n{system_prompt}"

    return agent, sandbox

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Autonomous Code Agent")
    parser.add_argument("--mode", type=str, choices=["local", "global"], default="global", 
                        help="Execution mode: 'local' (runs model on your GPU) or 'global' (uses HF API)")
    parser.add_argument("--prompt", type=str, required=True, help="The task for the agent to perform")
    parser.add_argument("--model", type=str, default=None, help="Optional: specify a custom model ID")
    args = parser.parse_args()

    agent, sandbox = None, None
    try:
        agent, sandbox = create_agent(mode=args.mode, model_id=args.model)
        
        print(f"\n--- Running Task in {args.mode.upper()} mode ---")
        print(f"Prompt: {args.prompt}\n")
        
        # Execute the agent
        result = agent.run(args.prompt)
        
        print("\n--- Result ---")
        print(result)
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if sandbox:
            print("\nCleaning up Docker sandbox...")
            sandbox.cleanup()
