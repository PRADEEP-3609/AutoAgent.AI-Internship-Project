import docker
import io
import tarfile
import os

class DockerSandboxExecutor:
    def __init__(self, image_name="code-agent-sandbox", container_name="smolagents-sandbox", authorized_dirs=None):
        self.client = docker.from_env()
        self.image_name = image_name
        self.container_name = container_name
        self.container = None
        self.authorized_dirs = authorized_dirs or [os.path.join(os.path.expanduser("~"), "Desktop")]
        self._ensure_image()
        self._start_container()

    def _ensure_image(self):
        try:
            self.client.images.get(self.image_name)
            print(f"Found Docker image: {self.image_name}")
        except docker.errors.ImageNotFound:
            print(f"Building Docker image {self.image_name}... This might take a moment.")
            # Build from the directory containing Dockerfile.sandbox
            build_path = os.path.dirname(os.path.abspath(__file__))
            self.client.images.build(path=build_path, dockerfile="Dockerfile.sandbox", tag=self.image_name)
            print(f"Successfully built {self.image_name}")

    def _start_container(self):
        # We must recreate the container to apply new volume mounts if the user changed them
        try:
            old_container = self.client.containers.get(self.container_name)
            old_container.stop()
            old_container.remove()
        except docker.errors.NotFound:
            pass

        print(f"Creating and starting new container: {self.container_name}")
        
        # Dynamically build the volume mapping from authorized_dirs
        volumes = {}
        for d in self.authorized_dirs:
            if os.path.exists(d):
                basename = os.path.basename(os.path.normpath(d))
                if not basename:
                    basename = d.replace(":\\", "_drive").replace(":/", "_drive")
                target = f'/home/agentuser/{basename}'
                volumes[d] = {'bind': target, 'mode': 'rw'}
                print(f"Mapped {d} -> {target}")

        self.container = self.client.containers.run(
            self.image_name,
            name=self.container_name,
            detach=True,
            mem_limit="512m",
            cpu_quota=50000, # 0.5 CPU
            security_opt=["no-new-privileges"],
            network_mode="bridge", # basic networking
            volumes=volumes
        )

    def execute_code(self, code: str) -> str:
        """Executes Python code inside the Docker container."""
        # Wrap code to catch exceptions, print stdout, and support final_answer
        wrapped_code = f"""
import sys
import traceback

def final_answer(result):
    print(f"\\n<<FINAL_ANSWER>>{{result}}<<FINAL_ANSWER>>\\n")
    return result

def web_search(query):
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=5)
        return str(list(results))
    except ImportError:
        return "Error: duckduckgo-search is not installed in the sandbox."

try:
{self._indent(code, 4)}
except Exception as e:
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
        
        script_content = wrapped_code.encode('utf-8')
        
        # Write code to a tar archive to copy into the container
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name='script.py')
            tarinfo.size = len(script_content)
            tar.addfile(tarinfo, io.BytesIO(script_content))
        
        tar_stream.seek(0)
        self.container.put_archive('/sandbox', tar_stream)
        
        # Execute the script
        exit_code, output = self.container.exec_run(["python", "/sandbox/script.py"])
        
        decoded_output = output.decode('utf-8')
        if exit_code != 0:
            return f"Execution failed with code {exit_code}:\n{decoded_output}"
        
        return decoded_output

    def _indent(self, text: str, amount: int) -> str:
        padding = " " * amount
        return "".join(padding + line + "\n" for line in text.splitlines())

    def send_variables(self, variables: dict):
        """Stub to support smolagents LocalPythonExecutor API."""
        pass

    def send_tools(self, tools: dict):
        """Stub to support smolagents LocalPythonExecutor API."""
        pass

    def __call__(self, code_action: str) -> tuple:
        """Callable interface expected by smolagents."""
        output = self.execute_code(code_action)
        
        final_result = None
        is_final_answer = False
        
        if "<<FINAL_ANSWER>>" in output:
            parts = output.split("<<FINAL_ANSWER>>")
            if len(parts) >= 3:
                final_result = parts[-2]
                is_final_answer = True
                
        return (final_result if is_final_answer else output, output, is_final_answer)

    def cleanup(self):
        """Stops and removes the sandbox container."""
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
                print(f"Cleaned up container: {self.container_name}")
            except Exception as e:
                print(f"Error during cleanup: {e}")
