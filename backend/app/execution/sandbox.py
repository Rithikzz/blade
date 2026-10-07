import subprocess
import tempfile
import os
import json
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def is_docker_available():
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def setup_docker_image():
    image_name = "veritas-sandbox:latest"
    try:
        subprocess.run(["docker", "image", "inspect", image_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        logger.info("Building veritas-sandbox Docker image...")
        dockerfile_content = "FROM python:3.11-slim\nRUN pip install pandas numpy duckdb==0.10.3 openpyxl\n"
        with tempfile.TemporaryDirectory() as build_dir:
            with open(os.path.join(build_dir, "Dockerfile"), "w") as f:
                f.write(dockerfile_content)
            subprocess.run(["docker", "build", "-t", image_name, build_dir], check=True)
    return image_name

def execute_in_sandbox(dataset_paths: dict, code: str) -> dict:
    has_docker = is_docker_available()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        runner_datasets_config = {}
        # Copy datasets
        for ds_id, info in dataset_paths.items():
            dataset_path = info["path"]
            var_name = info["var_name"]
            
            dataset_name = info.get("original_filename", Path(dataset_path).name)
            target_dataset_path = temp_dir_path / dataset_name
            shutil.copy2(dataset_path, target_dataset_path)
            
            runner_datasets_config[var_name] = dataset_name
            
        # If there's exactly 1 dataset, also add 'df' alias for backwards compatibility
        if len(dataset_paths) == 1:
             ds_id = list(dataset_paths.keys())[0]
             dataset_name = Path(dataset_paths[ds_id]["path"]).name
             runner_datasets_config["df"] = dataset_name
        
        # Write code
        code_path = temp_dir_path / "script.py"
        with open(code_path, "w") as f:
            f.write(code)
            
        # Write runner script
        runner_source_path = Path(__file__).parent / "runner_template.py"
        target_runner_path = temp_dir_path / "runner.py"
        shutil.copy2(runner_source_path, target_runner_path)
        
        # Write config
        config_path = temp_dir_path / "config.json"
        config_data = {
            "datasets": runner_datasets_config,
            "code_path": "script.py",
            "output_path": "output.json"
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)
        
        output_path = temp_dir_path / "output.json"
        
        timeout_seconds = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "15"))

        sandbox_type = "docker"
        if has_docker:
            image_name = setup_docker_image()
            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "512m",
                "--cpus", "1.0",
                "-v", f"{temp_dir_path.resolve()}:/sandbox",
                "-w", "/sandbox",
                image_name,
                "python", "runner.py", "config.json"
            ]
        else:
            sandbox_type = "local_subprocess (INSECURE)"
            cmd = [
                "python3", "runner.py", "config.json"
            ]
            
        try:
            cwd = temp_dir_path if not has_docker else None
            subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=True)
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timed out.", "sandbox_type": sandbox_type}
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "Unknown error"
            return {"success": False, "error": f"Execution failed: {err_msg}", "sandbox_type": sandbox_type}
            
        if not output_path.exists():
            return {"success": False, "error": "No output produced.", "sandbox_type": sandbox_type}
            
        with open(output_path, "r") as f:
            result = json.load(f)
            
        result["sandbox_type"] = sandbox_type
        return result
