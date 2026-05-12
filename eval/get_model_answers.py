import json
import logging
import os
import re
import sys

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "LlamaFactory", "src"))

from config import ANSWERS_FILE, FINE_TUNED_MODEL_PATH, MAX_TOKENS, ORIGINAL_MODEL_PATH, QUESTIONS_FILE
from llamafactory.chat import ChatModel

try:
    from transformers.utils import logging as hf_logging

    hf_logging.set_verbosity_error()
except Exception:
    pass

logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("llamafactory").setLevel(logging.ERROR)


def build_answer_prompt(question: str) -> str:
    return f"""请按电力运检现场作业要求回答下面问题。

作答要求：
1. 回答控制在 300-600 个中文字符，不能只给一句概括。
2. 使用分点结构，至少包含：判断/检查要点、关键操作步骤、主要风险点、安全控制措施。
3. 涉及规程或阈值时，如果不能确定具体数值，请说明“按现行规程或现场标准执行”，不要编造标准。
4. 避免危险操作建议，表达要专业、可执行、简洁。

问题：{question}
"""


def clean_model_answer(answer) -> str:
    """Extract plain response text from LlamaFactory chat response."""
    if hasattr(answer, "response_text"):
        text = answer.response_text
    elif hasattr(answer, "content"):
        text = answer.content
    else:
        text = str(answer)
        match = re.search(r"response_text='([\s\S]*?)', response_length=", text)
        if match:
            text = match.group(1)

    text = str(text).replace("\\n", "\n").strip()
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    return text


def build_chat_model(model_path: str, is_lora: bool = False) -> ChatModel:
    args = {
        "model_name_or_path": ORIGINAL_MODEL_PATH if is_lora else model_path,
        "template": "qwen3_5_nothink",
        "max_new_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }
    if is_lora:
        args["adapter_name_or_path"] = model_path

    return ChatModel(args)


def get_model_answer(model: ChatModel, question: str) -> str:
    response = model.chat([{"role": "user", "content": build_answer_prompt(question)}])
    return clean_model_answer(response[0])


def main():
    """Get answers from original and fine-tuned models."""
    if not os.path.exists(QUESTIONS_FILE):
        print(f"问题文件{QUESTIONS_FILE}不存在，请先运行 generate_questions.py")
        return False

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if not questions:
        print(f"问题文件{QUESTIONS_FILE}为空，请先成功生成评估问题")
        return False

    print(f"开始获取模型回答，共{len(questions)}个问题")

    print("\n加载原始模型...")
    original_model = build_chat_model(ORIGINAL_MODEL_PATH, is_lora=False)
    original_answers = []
    for i, question in enumerate(questions, 1):
        print(f"问题{i}: {question[:50]}...")
        answer = get_model_answer(original_model, question)
        original_answers.append(answer)
        print(f"原始模型回答: {answer[:100]}...")

    print("\n加载微调模型...")
    fine_tuned_model = build_chat_model(FINE_TUNED_MODEL_PATH, is_lora=True)
    fine_tuned_answers = []
    for i, question in enumerate(questions, 1):
        print(f"问题{i}: {question[:50]}...")
        answer = get_model_answer(fine_tuned_model, question)
        fine_tuned_answers.append(answer)
        print(f"微调模型回答: {answer[:100]}...")

    answers = {
        "questions": questions,
        "original_model": original_answers,
        "fine_tuned_model": fine_tuned_answers,
    }

    os.makedirs(os.path.dirname(ANSWERS_FILE), exist_ok=True)
    with open(ANSWERS_FILE, "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)

    print(f"\n成功获取两个模型的回答，已保存到{ANSWERS_FILE}")
    return True


if __name__ == "__main__":
    main()
