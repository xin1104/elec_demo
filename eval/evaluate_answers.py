import json
import random
from config import ANSWERS_FILE, EVALUATION_FILE, DEEPSEEK_API_KEY, DEEPSEEK_API_URL, MAX_TOKENS, TEMPERATURE
import requests

def blind_evaluate():
    """对两个模型的回答进行盲打分"""
    # 加载回答
    if not ANSWERS_FILE:
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
        
        # 随机打乱两个回答的顺序
        answers = [
            {"id": "A", "answer": original_answer},
            {"id": "B", "answer": fine_tuned_answer}
        ]
        random.shuffle(answers)
        
        # 显示打乱后的回答
        print("\n回答A:")
        print(answers[0]["answer"])
        print("\n回答B:")
        print(answers[1]["answer"])
        
        # 让用户打分
        score_a = float(input("请为回答A打分（0-100）: "))
        score_b = float(input("请为回答B打分（0-100）: "))
        
        # 记录结果
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
    
    # 计算总分
    original_total = 0
    fine_tuned_total = 0
    for result in results:
        if result["answer_a"]["id"] == "A":
            original_total += result["answer_a"]["score"]
            fine_tuned_total += result["answer_b"]["score"]
        else:
            original_total += result["answer_b"]["score"]
            fine_tuned_total += result["answer_a"]["score"]
    
    # 计算平均分
    original_avg = original_total / len(results)
    fine_tuned_avg = fine_tuned_total / len(results)
    
    # 保存评估结果
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
    
    # 输出结果
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

def auto_evaluate():
    """使用DeepSeek API自动评估回答"""
    # 加载回答
    if not ANSWERS_FILE:
        print(f"回答文件{ANSWERS_FILE}不存在，请先运行get_model_answers.py")
        return
    
    with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    questions = data["questions"]
    original_answers = data["original_model"]
    fine_tuned_answers = data["fine_tuned_model"]
    
    print(f"开始使用DeepSeek API自动评估{len(questions)}个问题的回答")
    
    results = []
    
    for i, (question, original_answer, fine_tuned_answer) in enumerate(zip(questions, original_answers, fine_tuned_answers), 1):
        print(f"\n评估问题{i}: {question[:50]}...")
        
        # 构建评估提示
        prompt = f"请作为电力运检领域的专家，对以下两个回答进行评分（0-100分）。评分标准：\n1. 准确性：回答是否正确，是否符合电力运检领域的专业知识\n2. 完整性：回答是否全面，是否覆盖了问题的各个方面\n3. 专业性：回答是否专业，是否使用了正确的术语和概念\n4. 清晰度：回答是否清晰易懂，逻辑是否连贯\n\n问题：{question}\n\n回答A：{original_answer}\n\n回答B：{fine_tuned_answer}\n\n请分别给出回答A和回答B的分数，并简要说明理由。\n\n输出格式：\nA: 分数\nB: 分数\n理由：\n..."
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一位电力运检领域的专家，擅长评估专业问题的回答质量。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE
        }
        
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response_json = response.json()
        
        if "choices" in response_json:
            content = response_json["choices"][0]["message"]["content"]
            print("DeepSeek评估结果:")
            print(content)
            
            # 解析分数
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
            
            # 记录结果
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
    
    # 计算总分
    original_total = sum(r["original_score"] for r in results)
    fine_tuned_total = sum(r["fine_tuned_score"] for r in results)
    
    # 计算平均分
    original_avg = original_total / len(results)
    fine_tuned_avg = fine_tuned_total / len(results)
    
    # 保存评估结果
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
    
    # 输出结果
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
    print("2. DeepSeek API自动评估")
    choice = input("请输入选项（1/2）: ")
    
    if choice == "1":
        blind_evaluate()
    elif choice == "2":
        auto_evaluate()
    else:
        print("无效选项，请重新运行。")

if __name__ == "__main__":
    main()
