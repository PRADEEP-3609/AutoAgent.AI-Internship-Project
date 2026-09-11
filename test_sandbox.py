from sandbox_executor import DockerSandboxExecutor

print("Initializing Docker Sandbox...")
sandbox = DockerSandboxExecutor()

code_to_run = """
import sys
import platform
import math

print(f"Hello from inside Docker!")
print(f"Python version: {platform.python_version()}")
print(f"Calculated Pi: {math.pi}")
"""

print("\nExecuting test code...")
output = sandbox.execute_code(code_to_run)
print("\n--- Sandbox Output ---")
print(output)
print("----------------------")

print("\nCleaning up...")
sandbox.cleanup()
print("Done.")
