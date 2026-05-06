import json
import random
import os
import sys
from config import ANSWERS_FILE, EVALUATION_FILE, DEEPSEEK_API_KEY, MAX_TOKENS, TEMPERATURE
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_options import ensure_api_config, prompt_api_config


def get_api_config():
    """获取 API 配置，如果配置中的密钥无效则提示用户选择服务商和模型"""
    try:
        return prompt_api_config(None if DEEPSEEK_API_KEY == "your_deepseek_api_key" else DEEPSEEK_API_KEY)
    except ValueError as exc:
        print(f"错误: {exc}")
        sys.exit(1)

def blind_evaluate():
    """对两个模型的回答进行盲打分"""
    if not os.path.exists(ANSWERS_FILE):
        print(f"回答文件{ANSWERS_FILE}不存在，请先运行get_model_answers.py")
        return

    with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data["questions"]
    original_answers = data["original_model"]
    fine_tuned_answers = data["fine_tuned_model"]

    print(f"开始对{len(questions)}个问题的回答进行盲评估")

    results = []

    for i, (question, original_answer, fine_tuned_answer) in enumerate(zip(questions, original_answers, fine_tuned_answers), 1):
        print(f"\n问题{i}: {question}")

        answers = [
            {"id": "A", "answer": original_answer},
            {"id": "B", "answer": fine_tuned_answer}
        ]
        random.shuffle(answers)

        print("\n回答A:")
        print(answers[0]["answer"])
        print("\n回答B:")
        print(answers[1]["answer"])

        score_a = float(input("请为回答A打分（0-100）: "))
        score_b = float(input("请为回答B打分（0-100）: "))

        result = {
            "question": question,
            "answer_a": {
                "id": answers[0]["id"],
                "score": score_a
            },
            "answer_b": {
                "id": answers[1]["id"],
                "score": score_b
            }
        }
        results.append(result)

    original_total = 0
    fine_tuned_total = 0
    for result in results:
        if result["answer_a"]["id"] == "A":
            original_total += result["answer_a"]["score"]
            fine_tuned_total += result["answer_b"]["score"]
        else:
            original_total += result["answer_b"]["score"]
            fine_tuned_total += result["answer_a"]["score"]

    original_avg = original_total / len(results)
    fine_tuned_avg = fine_tuned_total / len(results)

    evaluation = {
        "results": results,
        "original_model": {
            "total_score": original_total,
            "average_score": original_avg
        },
        "fine_tuned_model": {
            "total_score": fine_tuned_total,
            "average_score": fine_tuned_avg
        }
    }

    with open(EVALUATION_FILE, "w", encoding="utf-8") as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)

    print("\n" + "="*50)
    print("评估结果汇总")
    print("="*50)
    print(f"原始模型总分: {original_total:.2f}")
    print(f"原始模型平均分: {original_avg:.2f}")
    print(f"微调模型总分: {fine_tuned_total:.2f}")
    print(f"微调模型平均分: {fine_tuned_avg:.2f}")

    if fine_tuned_avg > original_avg:
        print("\n✅ 微调模型表现优于原始模型！")
        print(f"提升幅度: {((fine_tuned_avg - original_avg) / original_avg * 100):.2f}%")
    else:
        print("\n❌ 微调模型表现不如原始模型。")
        print(f"差距: {((original_avg - fine_tuned_avg) / original_avg * 100):.2f}%")

    print("\n评估结果已保存到evaluation_results.json")

def auto_evaluate(api_config=None):
    """使用所选 API 自动评估回答"""
    if api_config is None:
        api_config = get_api_config()
    else:
        api_config = ensure_api_config(api_config)

    if not os.path.exists(ANSWERS_FILE):
        print(f"回答文件{ANSWERS_FILE}不存在，请先运行get_model_answers.py")
        return

    with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data["questions"]
    original_answers = data["original_model"]
    fine_tuned_answers = data["fine_tuned_model"]

    print(f"开始使用{api_config.provider} API自动评估{len(questions)}个问题的回答")

    results = []

    for i, (question, original_answer, fine_tuned_answer) in enumerate(zip(questions, original_answers, fine_tuned_answers), 1):
        print(f"\n评估问题{i}: {question[:50]}...")

        prompt = (
            f"请作为电力运检领域的专家，对以下两个回答进行评分（0-100分）。评分标准：\n"
            "1. 准确性：回答是否正确，是否符合电力运检领域的专业知识\n"
            "2. 完整性：回答是否全面，是否覆盖了问题的各个方面\n"
            "3. 专业性：回答是否专业，是否使用了正确的术语和概念\n"
            "4. 清晰度：回答是否清晰易懂，逻辑是否连贯\n\n"
            f"问题：{question}\n\n"
            f"回答A：{original_answer}\n\n"
            f"回答B：{fine_tuned_answer}\n\n"
            "请分别给出回答A和回答B的分数，并简要说明理由。\n\n"
            "输出格式：\n"
            "A: 分数\n"
            "B: 分数\n"
            "理由："
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_config.api_key}"
        }

        payload = {
            "model": api_config.model,
            "messages": [
                {"role": "system", "content": "你是一位电力运检领域的专家，擅长评估专业问题的回答质量。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE
        }

        response = requests.post(api_config.api_url, headers=headers, json=payload)
        response_json = response.json()

        if "choices" in response_json:
            content = response_json["choices"][0]["message"]["content"]
            print(f"{api_config.provider}评估结果:")
            print(content)

            score_a = 0
            score_b = 0
            lines = content.strip().split("\n")
            for line in lines:
                if line.startswith("A:"):
                    try:
                        score_a = float(line.split(":")[1].strip())
                    except:
                        pass
                elif line.startswith("B:"):
                    try:
                        score_b = float(line.split(":")[1].strip())
                    except:
                        pass

            result = {
                "question": question,
                "original_answer": original_answer,
                "fine_tuned_answer": fine_tuned_answer,
                "original_score": score_a,
                "fine_tuned_score": score_b,
                "evaluation": content
            }
            results.append(result)
        else:
            print("评估失败：", response_json)
            result = {
                "question": question,
                "original_answer": original_answer,
                "fine_tuned_answer": fine_tuned_answer,
                "original_score": 0,
                "fine_tuned_score": 0,
                "evaluation": "评估失败"
            }
            results.append(result)

    original_total = sum(r["original_score"] for r in results)
    fine_tuned_total = sum(r["fine_tuned_score"] for r in results)

    original_avg = original_total / len(results) if results else 0
    fine_tuned_avg = fine_tuned_total / len(results) if results else 0

    evaluation = {
        "results": results,
        "original_model": {
            "total_score": original_total,
            "average_score": original_avg
        },
        "fine_tuned_model": {
            "total_score": fine_tuned_total,
            "average_score": fine_tuned_avg
        }
    }

    with open(EVALUATION_FILE, "w", encoding="utf-8") as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)

    print("\n" + "="*50)
    print("评估结果汇总")
    print("="*50)
    print(f"原始模型总分: {original_total:.2f}")
    print(f"原始模型平均分: {original_avg:.2f}")
    print(f"微调模型总分: {fine_tuned_total:.2f}")
    print(f"微调模型平均分: {fine_tuned_avg:.2f}")

    if fine_tuned_avg > original_avg:
        print("\n✅ 微调模型表现优于原始模型！")
        print(f"提升幅度: {((fine_tuned_avg - original_avg) / original_avg * 100):.2f}%")
    else:
        print("\n❌ 微调模型表现不如原始模型。")
        print(f"差距: {((original_avg - fine_tuned_avg) / original_avg * 100):.2f}%")

    print("\n评估结果已保存到evaluation_results.json")

def main():
    """主函数"""
    print("请选择评估方式：")
    print("1. 人工盲评估")
    print("2. API自动评估")
    choice = input("请输入选项（1/2）: ")

    if choice == "1":
        blind_evaluate()
    elif choice == "2":
        auto_evaluate()
    else:
        print("无效选项，请重新运行。")

if __name__ == "__main__":
    main()
