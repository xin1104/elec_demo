import os


DEEPSEEK_API_KEY = "your_deepseek_api_key"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ORIGINAL_MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    "model",
    "models--Qwen--Qwen3.5-0.8B-Base",
    "snapshots",
    "a9a407bcae463285164cc9133995c515379cebe5",
)

LORA_ROOT = os.path.join(
    PROJECT_ROOT,
    "saves",
    "Qwen3.5-0.8B-Base",
    "lora",
)


def find_latest_lora_adapter(root: str = LORA_ROOT) -> str:
    """Return the newest local LoRA adapter directory containing adapter_config.json."""
    candidates = []
    if not os.path.isdir(root):
        return os.path.join(root, "train_2026-05-11-22-12-12")

    for current_dir, _, files in os.walk(root):
        if "adapter_config.json" in files:
            candidates.append(current_dir)

    if not candidates:
        return os.path.join(root, "train_2026-05-11-22-12-12")

    return max(candidates, key=lambda path: os.path.getmtime(os.path.join(path, "adapter_config.json")))


FINE_TUNED_MODEL_PATH = find_latest_lora_adapter()

QUESTION_COUNT = 10
MAX_TOKENS = 1000
TEMPERATURE = 0.7

RESULT_DIR = os.path.join(PROJECT_ROOT, "result")
os.makedirs(RESULT_DIR, exist_ok=True)

QUESTIONS_FILE = os.path.join(RESULT_DIR, "questions.json")
ANSWERS_FILE = os.path.join(RESULT_DIR, "answers.json")
EVALUATION_FILE = os.path.join(RESULT_DIR, "evaluation_results.json")
