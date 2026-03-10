#!/usr/bin/env python3
"""
Download a GGUF model from Hugging Face and add it to the model cache.

Usage:
    python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"
    python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF" "Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf"

The script will attempt to find the file on Hugging Face and download it.
"""

import os
import sys
import argparse
from pathlib import Path

# Try to import huggingface_hub, with helpful error message if missing
try:
    from huggingface_hub import hf_hub_download, list_repo_files
except ImportError:
    print("ERROR: huggingface_hub is not installed.")
    print("Install it with: pip install huggingface_hub")
    sys.exit(1)

# Root of the repo (one level up from scripts/)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_model_repo(model_name: str) -> tuple[str, str]:
    """
    Attempt to find a GGUF model on Hugging Face.

    Args:
        model_name: Either a full repo ID (e.g., "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF")
                   or just a model filename (e.g., "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")

    Returns:
        Tuple of (repo_id, filename)
    """
    # If it looks like a repo ID (contains /)
    if "/" in model_name:
        repo_id = model_name
        # Try to find a .gguf file in this repo
        try:
            files = list_repo_files(repo_id, repo_type="model")
            gguf_files = [f for f in files if f.endswith(".gguf")]
            if gguf_files:
                # Prefer Q4_K_M if available, otherwise return the first
                preferred = next((f for f in gguf_files if "Q4_K_M" in f), gguf_files[0])
                return repo_id, preferred
            else:
                raise ValueError(f"No .gguf files found in {repo_id}")
        except Exception as e:
            raise ValueError(f"Could not access repository {repo_id}: {e}")

    # If it's just a filename, search for it on known repos
    else:
        known_repos = [
            "TheBloke",
            "mlabonne",
        ]

        for creator in known_repos:
            try:
                repo_attempts = [
                    f"{creator}/{model_name.replace('.gguf', '')}-GGUF",
                    f"{creator}/{model_name.replace('.gguf', '')}",
                ]

                for repo_id in repo_attempts:
                    try:
                        files = list_repo_files(repo_id, repo_type="model")
                        gguf_files = [f for f in files if model_name in f or f.endswith(".gguf")]
                        if gguf_files:
                            return repo_id, gguf_files[0]
                    except:
                        continue
            except:
                continue

        raise ValueError(
            f"Could not find '{model_name}' on Hugging Face.\n"
            f"Try specifying the full repo: 'bartowski/Meta-Llama-3.1-8B-Instruct-GGUF'"
        )


def _write_preset(cache_dir: str, filename: str) -> None:
    """Create the .yml preset file that llama-server router mode requires."""
    preset_name = Path(filename).stem
    preset_path = os.path.join(cache_dir, f"{preset_name}.yml")
    if os.path.exists(preset_path):
        print(f"[+] Preset already exists: {preset_path}")
        return
    content = f"model: /models/{filename}\nn_ctx: 8192\n"
    with open(preset_path, "w") as f:
        f.write(content)
    print(f"[+] Created preset: {preset_path}")
    print(f"\n[i] Model ready to use!")
    print(f"    Model ID: {preset_name}")
    print(f"    Restart the server: docker compose restart ai-server")


def download_model(model_input: str, cache_dir: str = None, filename: str = None) -> str:
    """
    Download a GGUF model to the cache directory.

    Args:
        model_input: Model repo ID or filename
        cache_dir: Directory to save the model (defaults to ../model_cache)
        filename: Specific .gguf filename to download (overrides auto-select)

    Returns:
        Path to the downloaded model
    """
    if cache_dir is None:
        cache_dir = os.path.join(_REPO_ROOT, "model_cache")

    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)

    print(f"[*] Looking for model: {model_input}")

    # Find the repo and filename
    repo_id, auto_filename = find_model_repo(model_input)
    filename = filename or auto_filename
    print(f"[+] Found: {repo_id}/{filename}")

    local_path = os.path.join(cache_dir, filename)
    if os.path.exists(local_path):
        size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"[+] Model already exists: {local_path} ({size_mb:.1f} MB)")
        _write_preset(cache_dir, filename)
        return local_path

    print(f"[~] Downloading {filename} ({repo_id})...")
    print(f"    Destination: {cache_dir}")

    try:
        local_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=cache_dir,
            local_dir_use_symlinks=False,
        )

        size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"[+] Downloaded successfully!")
        print(f"    Location: {local_path}")
        print(f"    Size: {size_mb:.1f} MB")

        _write_preset(cache_dir, filename)

        return local_path

    except Exception as e:
        print(f"[!] Download failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Download a GGUF model from Hugging Face to your local model cache.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-select Q4_K_M from a repo
  python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF"

  # Pick a specific quantization
  python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF" "Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf"

  # Specify a custom cache directory
  python scripts/download_model.py "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF" -c C:\\models

Popular GGUF Sources:
  - bartowski: https://huggingface.co/bartowski (recommended)
  - TheBloke:  https://huggingface.co/TheBloke
        """
    )

    parser.add_argument(
        "model",
        help='Model repo ID (e.g., "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF") or filename'
    )
    parser.add_argument(
        "-c", "--cache",
        help="Cache directory (defaults to ./model_cache)",
        default=None
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help='Specific .gguf filename to download (e.g., "model-Q4_K_M.gguf"). Defaults to Q4_K_M if available.',
        default=None,
    )
    args = parser.parse_args()

    download_model(args.model, args.cache, args.filename)


if __name__ == "__main__":
    main()
