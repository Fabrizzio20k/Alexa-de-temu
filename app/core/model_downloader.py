from pathlib import Path
import urllib.request


def download_model(url: str, output_path: Path):
    if output_path.exists():
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {output_path.name}...")
    urllib.request.urlretrieve(url, output_path)
    print(f"Downloaded {output_path.name}")


def download_llm_model():
    model_path = Path("models/soob3123_amoral-gemma3-12B-Q4_K_M.gguf")

    if model_path.exists():
        print("LLM model already exists, skipping download")
        return

    url = "https://huggingface.co/bartowski/soob3123_amoral-gemma3-12B-GGUF/resolve/main/soob3123_amoral-gemma3-12B-Q4_K_M.gguf?download=true"

    model_path.parent.mkdir(parents=True, exist_ok=True)

    print("Downloading LLM model (7.3GB)...")
    urllib.request.urlretrieve(url, model_path)
    print("LLM model downloaded!")


def ensure_models():
    download_llm_model()

    models_dir = Path("models")

    model_files = {
        "es_AR-daniela-high.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx",
        "es_AR-daniela-high.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx.json"
    }

    for filename, url in model_files.items():
        download_model(url, models_dir / filename)
