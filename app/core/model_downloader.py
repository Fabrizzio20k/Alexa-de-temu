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
    model_path = Path("models/qwen2.5-3b-instruct-q4_k_m.gguf")

    if model_path.exists():
        print("LLM model already exists, skipping download")
        return

    url = "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"

    model_path.parent.mkdir(parents=True, exist_ok=True)

    print("Downloading LLM model (2.0GB, may take several minutes)...")
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
