import json
import os
import re
import sys
from typing import Any

from config import DEEPSEEK_API_KEY, MAX_TOKENS, QUESTION_COUNT, QUESTIONS_FILE, TEMPERATURE
from api_utils import call_chat_completion

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_options import ensure_api_config, prompt_api_config


def get_api_config():
    """获取 API 配置。"""
    try:
        return prompt_api_config(None if DEEPSEEK_API_KEY == "your_deepseek_api_key" else DEEPSEEK_API_KEY)
    except ValueError as exc:
        print(f"错误: {exc}")
        sys.exit(1)


def _extract_json_block(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:].strip()
    elif content.startswith("```"):
        content = content[3:].strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", content)
    return match.group(1).strip() if match else content


def _normalize_questions(raw: Any) -> list[str]:
    if isinstance(raw, dict):
        raw = raw.get("questions", [])

    questions: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                question = item
            elif isinstance(item, dict):
                question = item.get("question") or item.get("content") or item.get("instruction") or ""
            else:
                question = ""

            question = str(question).strip()
            if question:
                questions.append(question)

    return questions


def parse_questions(content: str) -> list[str]:
    """Parse JSON first, then fall back to numbered lines."""
    try:
        return _normalize_questions(json.loads(_extract_json_block(content)))
    except json.JSONDecodeError:
        pass

    questions: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^(?:Q|问题)?\s*\d+\s*[\.、:：)\-]\s*", "", line, flags=re.IGNORECASE)
        if line.endswith("?") or line.endswith("？"):
            questions.append(line)

    return questions


def build_question_prompt(extra_note: str = "") -> str:
    return f"""请生成 {QUESTION_COUNT} 个用于评估电力运检模型的高质量专业问题。

覆盖范围必须均衡包含：
1. 变电站、箱式变电站、变压器、断路器、开关柜、电缆分支箱等设备运检。
2. 配电线路巡视、缺陷分类、隐患排查、雨季/高温/台风等特殊天气特巡。
3. 继电保护、倒闸操作、两票三制、安全监护、接地线和验电等安全规范。
4. 故障处置、应急抢修、风险研判、现场标准化作业。
5. 智能电网、在线监测、状态检修、数据化运维。

出题要求：
- 问题要具体、专业、可评价，不能是泛泛的“介绍一下”。
- 每个问题应能考察模型的操作流程、风险点、安全措施或专业判断。
- 不要给答案，不要解释。
- 必须只返回 JSON，不要 Markdown，不要代码块，不要额外文字。
- JSON 格式必须为：{{"questions": ["问题1", "问题2"]}}。
{extra_note}
"""


def generate_questions(api_config=None) -> list[str]:
    """生成电力运检领域的专业问题。"""
    api_config = get_api_config() if api_config is None else ensure_api_config(api_config)

    questions: list[str] = []
    for attempt in range(1, 4):
        note = "" if attempt == 1 else f"\n上一次只解析出 {len(questions)} 个问题，请严格按 JSON 格式重新生成 {QUESTION_COUNT} 个问题。"
        content = call_chat_completion(
            api_config,
            [
                {"role": "system", "content": "你是电力运检、配网运维和电力安全规程专家，擅长设计模型评估题。"},
                {"role": "user", "content": build_question_prompt(note)},
            ],
            max_tokens=max(MAX_TOKENS, 2000),
            temperature=TEMPERATURE,
            purpose="生成评估问题",
        )
        if not content:
            continue

        questions = parse_questions(content)
        if len(questions) >= QUESTION_COUNT:
            questions = questions[:QUESTION_COUNT]
            break

        print(f"只解析出{len(questions)}个问题，少于要求的{QUESTION_COUNT}个，准备重试。")

    if not questions:
        print("生成问题失败：没有解析出有效问题，未覆盖原有 questions.json。")
        return []

    os.makedirs(os.path.dirname(QUESTIONS_FILE), exist_ok=True)
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"成功生成{len(questions)}个电力运检领域的专业问题，已保存到{QUESTIONS_FILE}")
    return questions


if __name__ == "__main__":
    generate_questions()
