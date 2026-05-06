import json
import os
import requests
import sys
from config import DEEPSEEK_API_KEY, QUESTION_COUNT, MAX_TOKENS, TEMPERATURE, QUESTIONS_FILE

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_options import ApiConfig, ensure_api_config, prompt_api_config

def get_api_config():
    """获取 API 配置，如果配置中的密钥无效则提示用户选择服务商和模型"""
    try:
        return prompt_api_config(None if DEEPSEEK_API_KEY == "your_deepseek_api_key" else DEEPSEEK_API_KEY)
    except ValueError as exc:
        print(f"错误: {exc}")
        sys.exit(1)

def generate_questions(api_config=None):
    """生成电力运检领域的专业问题"""
    if api_config is None:
        api_config = get_api_config()
    else:
        api_config = ensure_api_config(api_config)

    prompt = (
        f"请生成{QUESTION_COUNT}个电力运检领域的专业问题，涵盖以下方面：\n"
        "1. 电力设备运检（如变压器、断路器、线路等）\n"
        "2. 继电保护配置与维护\n"
        "3. 配电线路运维技能\n"
        "4. 电力突发事件应急处理\n"
        "5. 智能电网发展趋势\n\n"
        "每个问题要专业、具体，能够测试模型对电力运检领域知识的掌握程度。"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_config.api_key}"
    }

    data = {
        "model": api_config.model,
        "messages": [
            {"role": "system", "content": "你是一位电力运检领域的专家，擅长生成专业、具体的技术问题。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }

    response = requests.post(api_config.api_url, headers=headers, json=data)
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
