import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "LlamaFactory", "src"))

from config import ORIGINAL_MODEL_PATH, FINE_TUNED_MODEL_PATH, QUESTIONS_FILE, ANSWERS_FILE, MAX_TOKENS
from llamafactory.chat import ChatModel

def get_model_answer(model_path, question, is_lora=False):
    """获取模型对问题的回答"""
    base_model_path = "../model/models--Qwen--Qwen3.5-0.8B-Base/snapshots/a9a407bcae463285164cc9133995c515379cebe5"

    args = {
        "model_name_or_path": base_model_path if is_lora else model_path,
        "template": "qwen3_5",
        "max_new_tokens": MAX_TOKENS,
        "temperature": 0.7
    }

    if is_lora:
        args["adapter_name_or_path"] = model_path

    model = ChatModel(args)

    messages = [
        {"role": "user", "content": question}
    ]

    response = model.chat(messages)
    return response[0].content if hasattr(response[0], 'content') else str(response[0])

def main():
    """获取两个模型对所有问题的回答"""
    if not os.path.exists(QUESTIONS_FILE):
        print(f"问题文件{QUESTIONS_FILE}不存在，请先运行generate_questions.py")
        return

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"开始获取模型回答，共{len(questions)}个问题")

    print("\n获取原始模型回答...")
    original_answers = []
    for i, question in enumerate(questions, 1):
        print(f"问题{i}: {question[:50]}...")
        answer = get_model_answer(ORIGINAL_MODEL_PATH, question, is_lora=False)
        original_answers.append(answer)
        print(f"原始模型回答: {answer[:100]}...")

    print("\n获取微调模型回答...")
    fine_tuned_answers = []
    for i, question in enumerate(questions, 1):
        print(f"问题{i}: {question[:50]}...")
        answer = get_model_answer(FINE_TUNED_MODEL_PATH, question, is_lora=True)
        fine_tuned_answers.append(answer)
        print(f"微调模型回答: {answer[:100]}...")

    answers = {
        "questions": questions,
        "original_model": original_answers,
        "fine_tuned_model": fine_tuned_answers
    }

    with open(ANSWERS_FILE, "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)

    print(f"\n成功获取两个模型的回答，已保存到{ANSWERS_FILE}")

if __name__ == "__main__":
    main()
