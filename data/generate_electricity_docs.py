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

PROCESS_REQUIREMENTS = [
    "判断依据与检查要点",
    "标准化作业步骤",
    "主要风险点与误操作后果",
    "安全控制措施",
    "异常处置流程",
    "复测复查与闭环记录",
]

DATA_ELEMENTS = [
    "红外测温记录",
    "绝缘电阻或接地电阻测量结果",
    "负荷电流与电压波动记录",
    "局放、油色谱或SF6状态监测数据",
    "缺陷照片、台账与历史缺陷对比",
    "保护动作、告警与遥信遥测记录",
]

SAFETY_BOUNDARIES = [
    "停电、验电、装设接地线的顺序要求",
    "操作票、工作票和监护复诵要求",
    "带电部位安全距离与遮栏设置",
    "不得擅自扩大工作范围",
    "不得用手触摸运行或转动部件",
    "不得编造标准阈值，无法确定时按现行规程或现场标准执行",
]

COMMON_SCENE_QUESTIONS = [
    "倒闸操作与两票三制执行",
    "验电接地与安全措施布置",
    "配电线路故障定位和隔离",
    "变压器油色谱异常研判",
    "开关柜局放和异常声响排查",
    "雨季、台风、高温等特巡",
    "应急抢修风险研判和安全监护",
    "在线监测数据支撑状态检修",
]

TARGET_CASES = [
    {
        "equipment": "主变压器",
        "scenario": "年度检修和油色谱异常复核",
        "scene_question": "变压器油色谱异常研判",
        "focus_items": ["油色谱数据分析", "乙炔超标风险", "停电检修安全措施", "复测复查闭环"],
    },
    {
        "equipment": "箱式变电站",
        "scenario": "定期巡检和雨季特巡",
        "scene_question": "箱式变电站巡检与缺陷分级",
        "focus_items": ["防潮检查", "绝缘缺陷识别", "接地系统复核", "缺陷分类"],
    },
    {
        "equipment": "高压开关柜",
        "scenario": "倒闸操作和局放异常排查",
        "scene_question": "倒闸操作与两票三制执行",
        "focus_items": ["操作票管理", "验电接地", "安全监护", "异常放电声响排查"],
    },
    {
        "equipment": "电缆分支箱",
        "scenario": "短路故障应急抢修",
        "scene_question": "电缆分支箱故障定位和隔离",
        "focus_items": ["故障定位", "停电许可", "现场安全监护", "恢复送电条件确认"],
    },
    {
        "equipment": "断路器",
        "scenario": "操作机构状态检查",
        "scene_question": "断路器机械特性和操作机构风险评估",
        "focus_items": ["分合闸线圈电流", "机械特性试验", "储能机构检查", "误动拒动风险"],
    },
    {
        "equipment": "10kV配电线路",
        "scenario": "高温大负荷特巡",
        "scene_question": "配电线路过热和弧垂风险研判",
        "focus_items": ["红外测温", "导线接头温升", "弧垂变化", "负荷电流分析"],
    },
    {
        "equipment": "继电保护装置",
        "scenario": "保护校验和安全监护",
        "scene_question": "继电保护装置校验安全监护",
        "focus_items": ["保护定值核对", "二次安全措施", "压板状态复核", "防误碰误动"],
    },
    {
        "equipment": "变电站站用电系统",
        "scenario": "全站停电应急处置",
        "scene_question": "全站停电风险研判和恢复送电",
        "focus_items": ["事故初判", "站用电恢复", "逐级送电", "信息报送"],
    },
    {
        "equipment": "配电自动化终端",
        "scenario": "数据化运维平台巡检优化",
        "scene_question": "巡检路径优化和缺陷分类",
        "focus_items": ["在线监测", "缺陷分类", "巡检路径优化", "工单闭环"],
    },
    {
        "equipment": "智能变电站合并单元和智能终端",
        "scenario": "通信中断告警处置",
        "scene_question": "智能变电站通信中断影响分析",
        "focus_items": ["保护采样中断", "GOOSE链路告警", "遥信遥测异常", "检修压板与安全隔离"],
    },
]

DANGEROUS_PHRASES = [
    "先验电、后合闸",
    "验电后合闸",
    "用手触摸风扇叶片",
    "带负荷拉合隔离开关",
    "未验电直接装设接地线",
    "未停电直接检修",
    "每日清扫绝缘子",
    "动平衡试验",
    "转子是否平衡",
]

NEGATION_WORDS = ["严禁", "禁止", "不得", "不能", "避免", "防止", "不应", "切勿", "杜绝"]


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


def build_random_plan(index: int | None = None, coverage_mode: bool = False) -> dict:
    category, style = random.choice(DOCUMENT_TYPES)
    if coverage_mode and index is not None:
        target = TARGET_CASES[(index - 1) % len(TARGET_CASES)]
        equipment = target["equipment"]
        scenario = target["scenario"]
        scene_question = target["scene_question"]
        focus_items = target["focus_items"]
    else:
        equipment = random.choice(EQUIPMENT_TOPICS)
        scenario = random.choice(SCENARIOS)
        scene_question = random.choice(COMMON_SCENE_QUESTIONS)
        focus_items = random.sample(DETAIL_FOCUS, k=4)

    process_items = random.sample(PROCESS_REQUIREMENTS, k=4)
    data_items = random.sample(DATA_ELEMENTS, k=3)
    safety_items = random.sample(SAFETY_BOUNDARIES, k=3)
    title_patterns = [
        "{scenario}期间{equipment}巡视与处置要点",
        "{equipment}{scenario}现场检查记录与整改建议",
        "{scenario}场景下{equipment}风险分析和运维措施",
        "{equipment}异常排查及{focus}管理要求",
        "{scenario}工作中{equipment}{focus}实施细则",
        "{equipment}{scene_question}现场作业与风险控制资料",
        "{scenario}条件下{equipment}缺陷研判和闭环处置案例",
    ]
    title = random.choice(title_patterns).format(
        equipment=equipment,
        scenario=scenario,
        focus=focus_items[0],
        scene_question=scene_question,
    )
    return {
        "category": category,
        "title": title,
        "angle": style,
        "equipment": equipment,
        "scenario": scenario,
        "focus_items": "、".join(focus_items),
        "process_items": "、".join(process_items),
        "data_items": "、".join(data_items),
        "safety_items": "、".join(safety_items),
        "scene_question": scene_question,
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
训练目标场景：{plan["scene_question"]}
必须覆盖的流程要素：{plan["process_items"]}
建议写入的数据要素：{plan["data_items"]}
必须体现的安全边界：{plan["safety_items"]}

写作要求：
1. 正文长度控制在 2400 到 3600 个中文字符之间，不要太短。
2. 内容要贴近真实电力运检资料，必须包含具体场景、设备名称、检查步骤、判断依据、风险点、处置建议、复查闭环等细节。
3. 不要编造真实单位、真实人名、真实项目编号或真实事故；可以使用“某供电所”“某10kV线路”“某台区”等脱敏表达。
4. 语言风格要自然，避免明显 AI 腔；不同段落要有信息密度，不要空泛套话。
5. 必须输出纯文本。不要使用 Markdown，不要使用星号加粗，不要使用 # 标题，不要使用代码块，不要使用表格。
6. 可以使用普通中文标题、自然段和“1.”“一、”这类普通编号，但标题前后不要添加任何装饰符号。
7. 直接输出资料正文，不要输出“好的”“以下是”等聊天前缀。
8. 至少包含 5 个清晰小节，建议包括：现场背景、检查/判断要点、作业步骤、风险控制、异常处置、复查闭环。
9. 至少写入 2 到 4 个脱敏的示例数据或状态描述，例如温度差异、绝缘电阻变化、告警信息、缺陷等级、负荷变化等；如果无法确定真实阈值，应写“按现行规程或现场标准执行”。
10. 必须明确 2 到 4 条错误做法或禁忌，并说明后果；严禁出现“未验电直接装设接地线”“带负荷拉合隔离开关”“用手触摸运行设备”等危险建议。
11. 资料要能支撑后续生成 300-650 字的流程型 QA，避免只写背景介绍或宏观意义。
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


def validate_document(content: str) -> tuple[bool, list[str]]:
    reasons = []
    length = len(content)
    if length < 1800:
        reasons.append(f"长度过短({length}字)")
    if length > 5000:
        reasons.append(f"长度过长({length}字)")

    required_terms = ["风险", "检查", "措施", "处置", "复查"]
    missing_terms = [term for term in required_terms if term not in content]
    if missing_terms:
        reasons.append(f"缺少关键词: {'、'.join(missing_terms)}")

    if not re.search(r"(1[.、]|一、|（一）)", content):
        reasons.append("缺少结构化小节")

    if has_dangerous_advice(content):
        reasons.append("包含危险或明显错误表述")

    if re.search(r"(.{4,24})\1{3,}", content):
        reasons.append("存在重复退化")

    numeric_or_status = re.findall(r"(\d+(?:\.\d+)?\s*(?:kV|A|℃|Ω|MΩ|%|次|小时|分钟)|告警|缺陷|异常|合格|不合格)", content)
    if len(numeric_or_status) < 4:
        reasons.append("缺少检测数据或状态描述")

    return not reasons, reasons


def has_dangerous_advice(content: str) -> bool:
    for phrase in DANGEROUS_PHRASES:
        start = 0
        while True:
            index = content.find(phrase, start)
            if index == -1:
                break
            prefix = content[max(0, index - 12) : index]
            if not any(word in prefix for word in NEGATION_WORDS):
                return True
            start = index + len(phrase)
    return False


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
        "temperature": 0.65,
        "max_tokens": 5200,
    }
    if api_config.provider == "Xiaomi MiMo":
        payload["enable_thinking"] = False
        payload["thinking_budget"] = 0

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


def generate_valid_document(api_config, prompt: str, retries: int = 3) -> tuple[str | None, list[str]]:
    last_reasons = []
    for attempt in range(1, retries + 1):
        content = call_chat_completion(api_config, prompt)
        ok, reasons = validate_document(content)
        if ok:
            return content, []

        last_reasons = reasons
        print(f"资料质检未通过，第 {attempt}/{retries} 次: {'；'.join(reasons)}")
        prompt = (
            prompt
            + "\n\n上一版资料未通过质检，问题如下："
            + "；".join(reasons)
            + "\n请重新生成，严格补足缺失项，仍然只输出资料正文。"
        )

    return None, last_reasons


def main():
    print("电力资料批量生成工具")
    print("=" * 50)
    api_config = prompt_api_config()
    count = ask_positive_int("请输入要生成的资料数量: ")
    coverage_mode = input("是否启用评估主题覆盖模式？建议输入 y (y/n): ").strip().lower() != "n"
    print(f"\n开始生成 {count} 篇资料，输出目录: {OUTPUT_DIR}")

    created_files = []
    for index in range(1, count + 1):
        plan = build_random_plan(index=index, coverage_mode=coverage_mode)
        print(f"\n[{index}/{count}] 生成《{plan['title']}》...")
        prompt = build_prompt(index, count, plan)
        while True:
            try:
                content, reasons = generate_valid_document(api_config, prompt)
                if not content:
                    print(f"生成失败: 资料连续未通过质检: {'；'.join(reasons)}")
                    break
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
