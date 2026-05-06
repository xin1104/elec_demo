import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

import requests


sys.path.append(str(Path(__file__).resolve().parents[1]))
from api_options import prompt_api_config


OUTPUT_DIR = Path(__file__).resolve().parent

DOCUMENT_TYPES = [
    ("运维规程", "以基层班组制度或作业指导书口吻写，突出步骤、风险点、记录要求和闭环管理。"),
    ("故障分析", "以故障复盘材料口吻写，包含现象、排查、判断、处置、复盘和预防措施。"),
    ("培训资料", "以培训讲义口吻写，适合新员工或班组成员学习，解释概念并给出现场注意事项。"),
    ("技术论文", "以短篇技术分析文章口吻写，包含背景、机理、典型场景、治理措施和效果分析。"),
    ("应急预案", "以应急处置方案口吻写，包含响应分级、人员分工、物资准备、现场控制和信息报送。"),
    ("设备手册", "以设备运检手册口吻写，说明检测方法、异常判断、复测流程和处理建议。"),
    ("巡检纪要", "以班组现场纪要口吻写，包含发现问题、风险分析、责任分工、整改期限和复查要求。"),
    ("标准解读", "以标准宣贯材料口吻写，解释管理要求、执行要点、台账记录和常见偏差。"),
    ("案例教材", "以现场案例教材口吻写，包含报修背景、排查路径、测量数据、结论和启示。"),
    ("专项方案", "以专项治理方案口吻写，包含治理目标、排查范围、实施步骤、验收标准和持续改进。"),
]

EQUIPMENT_TOPICS = [
    "10kV架空线路", "配电变压器", "环网柜", "柱上断路器", "电缆分支箱", "低压台区",
    "箱式变电站", "避雷器", "跌落式熔断器", "继电保护装置", "配电自动化终端", "接地装置",
    "电缆终端头", "开关柜", "无功补偿装置", "计量箱", "绝缘安全工器具", "充电桩配电设施",
]

SCENARIOS = [
    "雨季特巡", "高温大负荷", "雷雨后复查", "春节保供电", "台风抢修", "迎峰度夏",
    "夜间测温", "春检整改", "外破风险防控", "树障清理", "低电压治理", "频繁跳闸排查",
    "设备老化治理", "隐患闭环管理", "新投运验收", "重要用户保电", "山区线路巡检", "电缆沟积水治理",
]

DETAIL_FOCUS = [
    "缺陷分级", "红外测温", "绝缘电阻测试", "负荷电流分析", "接地电阻测试", "局部放电检测",
    "保护定值核对", "操作票管理", "现场安全监护", "停送电许可", "通道环境治理", "台账复核",
    "备品备件准备", "抢修复电条件确认", "班前会风险交底", "图纸与现场一致性核查",
]


class ApiRequestError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def ask_positive_int(prompt: str) -> int:
    while True:
        value = input(prompt).strip()
        if value.isdigit() and int(value) > 0:
            return int(value)
        print("请输入大于 0 的整数。")


def safe_filename(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", "", text)
    return text[:80]


def build_random_plan() -> dict:
    category, style = random.choice(DOCUMENT_TYPES)
    equipment = random.choice(EQUIPMENT_TOPICS)
    scenario = random.choice(SCENARIOS)
    focus_items = random.sample(DETAIL_FOCUS, k=4)
    title_patterns = [
        "{scenario}期间{equipment}巡视与处置要点",
        "{equipment}{scenario}现场检查记录与整改建议",
        "{scenario}场景下{equipment}风险分析和运维措施",
        "{equipment}异常排查及{focus}管理要求",
        "{scenario}工作中{equipment}{focus}实施细则",
    ]
    title = random.choice(title_patterns).format(
        equipment=equipment,
        scenario=scenario,
        focus=focus_items[0],
    )
    return {
        "category": category,
        "title": title,
        "angle": style,
        "equipment": equipment,
        "scenario": scenario,
        "focus_items": "、".join(focus_items),
    }


def build_prompt(index: int, total: int, plan: dict) -> str:
    return f"""请生成一篇中文电力行业资料，用于构造电力运检领域训练数据。

资料序号：{index}/{total}
资料类型：{plan["category"]}
建议标题：{plan["title"]}
写作角度：{plan["angle"]}
涉及设备：{plan["equipment"]}
现场场景：{plan["scenario"]}
重点细节：{plan["focus_items"]}

写作要求：
1. 正文长度控制在 1800 到 2600 个中文字符之间，不要太短。
2. 内容要贴近真实电力运检资料，包含具体场景、设备名称、检查步骤、风险点、处置建议、复查闭环等细节。
3. 不要编造真实单位、真实人名、真实项目编号或真实事故；可以使用“某供电所”“某10kV线路”“某台区”等脱敏表达。
4. 语言风格要自然，避免明显 AI 腔；不同段落要有信息密度，不要空泛套话。
5. 必须输出纯文本。不要使用 Markdown，不要使用星号加粗，不要使用 # 标题，不要使用代码块，不要使用表格。
6. 可以使用普通中文标题、自然段和“1.”“一、”这类普通编号，但标题前后不要添加任何装饰符号。
7. 直接输出资料正文，不要输出“好的”“以下是”等聊天前缀。
"""


def normalize_plain_text(content: str) -> str:
    content = content.strip()
    content = re.sub(r"```(?:\w+)?", "", content)
    content = content.replace("```", "")
    content = re.sub(r"^\s{0,3}#{1,6}\s*", "", content, flags=re.MULTILINE)
    content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
    content = re.sub(r"__(.*?)__", r"\1", content)
    content = re.sub(r"(?m)^\s*[-*+]\s+", "", content)
    content = re.sub(r"(?m)^(\s*)>\s+", r"\1", content)
    content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def call_chat_completion(api_config, prompt: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_config.api_key}",
    }
    payload = {
        "model": api_config.model,
        "messages": [
            {
                "role": "system",
                "content": "你是一名熟悉配电、变电、继电保护和电力安全管理的资料编写专家。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.85,
        "max_tokens": 3500,
    }

    response = requests.post(api_config.api_url, headers=headers, json=payload, timeout=120)
    if response.status_code != 200:
        raise ApiRequestError(f"API 请求失败，状态码 {response.status_code}: {response.text}", response.status_code)

    data = response.json()
    try:
        return normalize_plain_text(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"API 响应格式不符合预期: {json.dumps(data, ensure_ascii=False)[:1000]}") from exc


def save_document(index: int, plan: dict, content: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"AI生成_{index:03d}_{safe_filename(plan['category'])}_{safe_filename(plan['title'])}_{timestamp}.txt"
    path = OUTPUT_DIR / filename
    path.write_text(content + "\n", encoding="utf-8")
    return path


def main():
    print("电力资料批量生成工具")
    print("=" * 50)
    api_config = prompt_api_config()
    count = ask_positive_int("请输入要生成的资料数量: ")
    print(f"\n开始生成 {count} 篇资料，输出目录: {OUTPUT_DIR}")

    created_files = []
    for index in range(1, count + 1):
        plan = build_random_plan()
        print(f"\n[{index}/{count}] 生成《{plan['title']}》...")
        prompt = build_prompt(index, count, plan)
        while True:
            try:
                content = call_chat_completion(api_config, prompt)
                path = save_document(index, plan, content)
                created_files.append(path)
                print(f"已保存: {path.name}，长度 {len(content)} 字符")
                break
            except ApiRequestError as exc:
                print(f"生成失败: {exc}")
                if exc.status_code not in {400, 401}:
                    break

                if exc.status_code == 401:
                    print("当前 API key 未通过服务端校验，请重新选择服务商/模型并输入新的 API key。")
                else:
                    print("当前模型或请求参数未通过服务端校验，请重新选择服务商/模型后重试。")

                retry = input("是否重试当前资料？(y/n): ").strip().lower()
                if retry != "y":
                    break
                api_config = prompt_api_config()
            except Exception as exc:
                print(f"生成失败: {exc}")
                break

    print("\n生成完成")
    print(f"成功生成 {len(created_files)}/{count} 篇资料")
    for path in created_files:
        print(f"- {path.name}")


if __name__ == "__main__":
    main()
