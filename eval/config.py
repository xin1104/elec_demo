# 配置文件

# DeepSeek API 配置
DEEPSEEK_API_KEY = "your_deepseek_api_key"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 模型配置
ORIGINAL_MODEL_PATH = "Qwen/Qwen3.5-0.8B-Instruct"
FINE_TUNED_MODEL_PATH = "saves/Qwen3.5-0.8B-Base/lora/train_2026-04-12-00-04-45/checkpoint-42"

# 评估配置
QUESTION_COUNT = 10  # 生成的问题数量
MAX_TOKENS = 1000  # 模型回答的最大令牌数
TEMPERATURE = 0.7  # 生成温度

# 文件路径
QUESTIONS_FILE = "questions.json"
ANSWERS_FILE = "answers.json"
EVALUATION_FILE = "evaluation_results.json"
