import json
import sys
import os

# 添加LlamaFactory到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "LlamaFactory"))

from config import ORIGINAL_MODEL_PATH, FINE_TUNED_MODEL_PATH, QUESTIONS_FILE, ANSWERS_FILE, MAX_TOKENS
from llamafactory.chat.chat_model import ChatModel
from llamafactory.data.template import get_template

def get_model_answer(model_path, question):
    """获取模型对问题的回答"""
    # 初始化模型
    template = get_template("qwen3_5")
    model = ChatModel(
        model_path=model_path,
        template=template,
        max_new_tokens=MAX_TOKENS,
        temperature=0.7
    )
    
    # 构建消息
    messages = [
        {"role": "user", "content": question}
    ]
    
    # 获取回答
    response = model.chat(messages)
    return response

def main():
    """获取两个模型对所有问题的回答"""
    # 加载问题
    if not os.path.exists(QUESTIONS_FILE):
        print(f"问题文件{QUESTIONS_FILE}不存在，请先运行generate_questions.py")
        return
    
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
    
    print(f"开始获取模型回答，共{len(questions)}个问题")
    
    # 获取原始模型回答
    print("\n获取原始模型回答...")
    original_answers = []
    for i, question in enumerate(questions, 1):
        print(f"问题{i}: {question[:50]}...")
        answer = get_model_answer(ORIGINAL_MODEL_PATH, question)
        original_answers.append(answer)
        print(f"原始模型回答: {answer[:100]}...")
    
    # 获取微调模型回答
    print("\n获取微调模型回答...")
    fine_tuned_answers = []
    for i, question in enumerate(questions, 1):
        print(f"问题{i}: {question[:50]}...")
        answer = get_model_answer(FINE_TUNED_MODEL_PATH, question)
        fine_tuned_answers.append(answer)
        print(f"微调模型回答: {answer[:100]}...")
    
    # 保存回答
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
