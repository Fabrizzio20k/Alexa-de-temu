from pathlib import Path
import urllib.request


def download_model(url: str, output_path: Path):
    if output_path.exists():
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {output_path.name}...")
    urllib.request.urlretrieve(url, output_path)
    print(f"Downloaded {output_path.name}")


def ensure_models():
    models_dir = Path("models")

    model_files = {
        "es_AR-daniela-high.onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx",
        "es_AR-daniela-high.onnx.json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx.json"
    }

    for filename, url in model_files.items():
        download_model(url, models_dir / filename)
