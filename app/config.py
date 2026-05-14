from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = BASE_DIR / "configs" / "default.yaml"

UPLOAD_DIR = BASE_DIR / "data" / "uploads"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"
RESULT_DIR = BASE_DIR / "data" / "results"
WEIGHT_DIR = BASE_DIR / "weights"

for path in [UPLOAD_DIR, OUTPUT_DIR, RESULT_DIR, WEIGHT_DIR]:
    path.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data or {}


CONFIG = load_config()


def get_model_path() -> str:
    model_cfg = CONFIG.get("model", {})
    weight_path = model_cfg.get("weight_path", "weights/yolov8m.pt")
    return str(BASE_DIR / weight_path)


def get_default_fps() -> int:
    return int(CONFIG.get("video", {}).get("default_fps", 30))


def get_output_size() -> tuple[int, int]:
    video_cfg = CONFIG.get("video", {})
    width = int(video_cfg.get("output_width", 960))
    height = int(video_cfg.get("output_height", 540))
    return width, height