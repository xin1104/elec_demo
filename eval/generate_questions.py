import json
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, QUESTION_COUNT, MAX_TOKENS, TEMPERATURE, QUESTIONS_FILE

def generate_questions():
    """生成电力运检领域的专业问题"""
    prompt = f"请生成{QUESTION_COUNT}个电力运检领域的专业问题，涵盖以下方面：
1. 电力设备运检（如变压器、断路器、线路等）
2. 继电保护配置与维护
3. 配电线路运维技能
4. 电力突发事件应急处理
5. 智能电网发展趋势

每个问题要专业、具体，能够测试模型对电力运检领域知识的掌握程度。""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一位电力运检领域的专家，擅长生成专业、具体的技术问题。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }

    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
    response_json = response.json()

    if "choices" in response_json:
        content = response_json["choices"][0]["message"]["content"]
        # 解析生成的问题
        questions = []
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and (line.startswith("Q") or line.startswith("问题") or line[0].isdigit()):
                # 提取问题内容
                if ". " in line:
                    question = line.split(". ", 1)[1]
                elif ": " in line:
                    question = line.split(": ", 1)[1]
                else:
                    question = line
                questions.append(question)
        
        # 确保生成足够的问题
        if len(questions) < QUESTION_COUNT:
            print(f"只生成了{len(questions)}个问题，少于要求的{QUESTION_COUNT}个")
        
        # 保存问题到文件
        with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        
        print(f"成功生成{len(questions)}个电力运检领域的专业问题，已保存到{QUESTIONS_FILE}")
        return questions
    else:
        print("生成问题失败：", response_json)
        return []

if __name__ == "__main__":
    generate_questions()
