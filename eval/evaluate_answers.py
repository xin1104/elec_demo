import json
import os
import random
import re
import sys
import time
from typing import Any

import requests

from config import ANSWERS_FILE, DEEPSEEK_API_KEY, EVALUATION_FILE, RESULT_DIR

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_options import ensure_api_config, prompt_api_config


MAX_EVAL_ANSWER_CHARS = 1200
JUDGE_RETRIES = 3
EVALUATION_DEBUG_FILE = os.path.join(RESULT_DIR, "evaluation_debug.json")


def get_api_config():
    """Get API config."""
    try:
        return prompt_api_config(None if DEEPSEEK_API_KEY == "your_deepseek_api_key" else DEEPSEEK_API_KEY)
    except ValueError as exc:
        print(f"错误: {exc}")
        sys.exit(1)


def clean_answer_text(text: str, limit: int = MAX_EVAL_ANSWER_CHARS) -> str:
    """Remove wrappers, thinking traces, and overlong tails before judging."""
    text = str(text)
    match = re.search(r"response_text='([\s\S]*?)', response_length=", text)
    if match:
        text = match.group(1)

    text = text.replace("\\n", "\n")
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > limit:
        return text[:limit] + "\n...[已截断，仅保留前部用于评分]"

    return text


def _load_answers():
    if not os.path.exists(ANSWERS_FILE):
        print(f"回答文件 {ANSWERS_FILE} 不存在，请先运行 get_model_answers.py")
        return None

    with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    original_answers = [clean_answer_text(item) for item in data.get("original_model", [])]
    fine_tuned_answers = [clean_answer_text(item) for item in data.get("fine_tuned_model", [])]
    if not questions:
        print(f"回答文件 {ANSWERS_FILE} 中没有问题，无法评估。")
        return None

    return questions, original_answers, fine_tuned_answers


def _safe_percent(delta: float, base: float) -> str:
    if base == 0:
        return "无法计算（基准平均分为 0）"
    return f"{delta / base * 100:.2f}%"


def _print_summary(original_total: float, fine_tuned_total: float, original_avg: float, fine_tuned_avg: float) -> None:
    print("\n" + "=" * 50)
    print("评估结果汇总")
    print("=" * 50)
    print(f"原始模型总分: {original_total:.2f}")
    print(f"原始模型平均分: {original_avg:.2f}")
    print(f"微调模型总分: {fine_tuned_total:.2f}")
    print(f"微调模型平均分: {fine_tuned_avg:.2f}")

    if fine_tuned_avg > original_avg:
        print("\n微调模型表现优于原始模型。")
        print(f"提升幅度: {_safe_percent(fine_tuned_avg - original_avg, original_avg)}")
    elif fine_tuned_avg < original_avg:
        print("\n微调模型表现不如原始模型。")
        print(f"差距: {_safe_percent(original_avg - fine_tuned_avg, original_avg)}")
    else:
        print("\n两个模型平均分相同。")


def _save_evaluation(results: list[dict], original_total: float, fine_tuned_total: float) -> None:
    original_avg = original_total / len(results) if results else 0
    fine_tuned_avg = fine_tuned_total / len(results) if results else 0
    evaluation = {
        "results": results,
        "original_model": {
            "total_score": original_total,
            "average_score": original_avg,
        },
        "fine_tuned_model": {
            "total_score": fine_tuned_total,
            "average_score": fine_tuned_avg,
        },
    }

    os.makedirs(os.path.dirname(EVALUATION_FILE), exist_ok=True)
    with open(EVALUATION_FILE, "w", encoding="utf-8") as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)

    _print_summary(original_total, fine_tuned_total, original_avg, fine_tuned_avg)
    print(f"\n评估结果已保存到 {EVALUATION_FILE}")


def blind_evaluate():
    """Manually blind-score the two model answers."""
    loaded = _load_answers()
    if loaded is None:
        return False

    questions, original_answers, fine_tuned_answers = loaded
    print(f"开始对 {len(questions)} 个问题的回答进行人工盲评")

    results = []
    original_total = 0.0
    fine_tuned_total = 0.0
    for i, (question, original_answer, fine_tuned_answer) in enumerate(zip(questions, original_answers, fine_tuned_answers), 1):
        print(f"\n问题 {i}: {question}")
        answers = [
            {"id": "original", "answer": original_answer},
            {"id": "fine_tuned", "answer": fine_tuned_answer},
        ]
        random.shuffle(answers)

        print("\n回答 A:")
        print(answers[0]["answer"])
        print("\n回答 B:")
        print(answers[1]["answer"])

        score_a = float(input("请为回答 A 打分（0-100）: "))
        score_b = float(input("请为回答 B 打分（0-100）: "))

        scores = {answers[0]["id"]: score_a, answers[1]["id"]: score_b}
        original_total += scores["original"]
        fine_tuned_total += scores["fine_tuned"]
        results.append(
            {
                "question": question,
                "original_answer": original_answer,
                "fine_tuned_answer": fine_tuned_answer,
                "original_score": scores["original"],
                "fine_tuned_score": scores["fine_tuned"],
                "evaluation": "manual blind evaluation",
            }
        )

    _save_evaluation(results, original_total, fine_tuned_total)
    return True


def _build_evaluation_prompt(question: str, answer_a: str, answer_b: str) -> str:
    return f"""请作为电力运检模型评测员，只做最终评分，不要展开推理。

评分维度总分 100：
- 准确性 35：是否符合电力设备运检、安全规程和现场作业要求。
- 完整性 25：是否覆盖关键步骤、检查项目、风险点、处置流程和注意事项。
- 专业性 20：术语是否规范，判断是否有依据，是否避免编造规范。
- 可执行性 10：现场人员能否据此操作或排查。
- 清晰度 10：结构是否清楚，表达是否简明。

扣分要求：存在明显安全风险、错误规程、危险操作建议时大幅扣分。不要因为回答更长就给高分。

只输出一行 JSON，不要 Markdown，不要解释过程。格式必须完全如下：
{{"answer_a_score": 85, "answer_b_score": 78, "reason": "不超过40字的简要依据"}}

问题：{question}

回答 A：
{answer_a}

回答 B：
{answer_b}
"""


def _extract_json_block(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:].strip()
    elif content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()

    match = re.search(r"\{[\s\S]*?\}", content)
    return match.group(0) if match else content


def _clip_score(value: Any) -> float:
    return max(0.0, min(100.0, float(value)))


def _parse_score(content: str) -> tuple[float | None, float | None, str]:
    content = (content or "").strip()
    if not content:
        return None, None, ""

    try:
        data = json.loads(_extract_json_block(content))
        original_score = _clip_score(data.get("original_score", data.get("answer_a_score")))
        fine_tuned_score = _clip_score(data.get("fine_tuned_score", data.get("answer_b_score")))
        reason = str(data.get("reason", "")).strip()[:80]
        return original_score, fine_tuned_score, reason or "按准确性、完整性、专业性等维度评分"
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass

    patterns = [
        (
            r"(?:original_score|原始模型(?:总分|评分|得分)?)[^\d]{0,20}(\d+(?:\.\d+)?)",
            r"(?:fine_tuned_score|微调模型(?:总分|评分|得分)?)[^\d]{0,20}(\d+(?:\.\d+)?)",
        ),
        (
            r"(?:answer_a_score|回答\s*A|A)[^\d]{0,20}(\d+(?:\.\d+)?)",
            r"(?:answer_b_score|回答\s*B|B)[^\d]{0,20}(\d+(?:\.\d+)?)",
        ),
        (
            r"原始[^\d]{0,20}(\d+(?:\.\d+)?)",
            r"微调[^\d]{0,20}(\d+(?:\.\d+)?)",
        ),
    ]
    for original_pattern, fine_tuned_pattern in patterns:
        original_match = re.search(original_pattern, content, re.IGNORECASE)
        fine_tuned_match = re.search(fine_tuned_pattern, content, re.IGNORECASE)
        if original_match and fine_tuned_match:
            return _clip_score(original_match.group(1)), _clip_score(fine_tuned_match.group(1)), "API未返回标准JSON，已提取分数"

    return None, None, content[:80]


def _compact_reason(reason: str) -> str:
    reason = re.sub(r"\s+", " ", reason or "").strip()
    if not reason:
        return "按评分维度综合判断"
    return reason[:80]


def _model_label(model_id: str) -> str:
    return "原始模型" if model_id == "original" else "微调模型"


def _format_blind_reason(reason: str, answer_a_id: str, answer_b_id: str) -> str:
    reason = _compact_reason(reason)
    return f"盲评顺序：A={_model_label(answer_a_id)}，B={_model_label(answer_b_id)}；{reason}"


def _fallback_score(answer: str) -> float:
    """Conservative local fallback used only when the judge API cannot return scores."""
    text = clean_answer_text(answer, limit=2000)
    if not text:
        return 0.0

    score = 45.0
    length = len(text)
    if length >= 120:
        score += 10
    if length >= 300:
        score += 10
    if length >= 700:
        score += 5

    positive_terms = [
        "停电",
        "验电",
        "接地",
        "安全",
        "记录",
        "检查",
        "风险",
        "处置",
        "标准",
        "绝缘",
        "试验",
        "巡视",
        "监测",
    ]
    score += min(20, sum(1 for term in positive_terms if term in text) * 2)

    if re.search(r"(每日清扫|转子|动平衡|GIS监控系统.*母线)", text):
        score -= 18
    if "四不放过" in text and "应急抢修" in text:
        score -= 8

    return round(_clip_score(score), 1)


def _request_judge(api_config, prompt: str, purpose: str) -> tuple[str | None, str | None, list[dict]]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_config.api_key}",
    }
    payload = {
        "model": api_config.model,
        "messages": [
            {"role": "system", "content": "你是严格评分器。只输出一行JSON，不输出推理过程。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 256,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    if api_config.provider == "Xiaomi MiMo":
        payload["enable_thinking"] = False
        payload["thinking_budget"] = 0

    debug_attempts = []
    for attempt in range(1, JUDGE_RETRIES + 1):
        try:
            response = requests.post(api_config.api_url, headers=headers, json=payload, timeout=60)
            if response.status_code >= 400:
                # Some OpenAI-compatible providers reject response_format or thinking flags.
                fallback_payload = dict(payload)
                fallback_payload.pop("response_format", None)
                fallback_payload.pop("enable_thinking", None)
                fallback_payload.pop("thinking_budget", None)
                response = requests.post(api_config.api_url, headers=headers, json=fallback_payload, timeout=60)

            response.raise_for_status()
            response_json = response.json()
            message = response_json.get("choices", [{}])[0].get("message", {})
            content = (message.get("content") or "").strip()
            reasoning_content = (message.get("reasoning_content") or "").strip()
            debug_attempts.append(
                {
                    "attempt": attempt,
                    "status_code": response.status_code,
                    "finish_reason": response_json.get("choices", [{}])[0].get("finish_reason"),
                    "content": content,
                    "reasoning_content": reasoning_content[:1200],
                    "usage": response_json.get("usage", {}),
                }
            )
            if content:
                return content, None, debug_attempts

            if reasoning_content:
                original_score, fine_tuned_score, _ = _parse_score(reasoning_content)
                if original_score is not None and fine_tuned_score is not None:
                    extracted = json.dumps(
                        {
                            "original_score": original_score,
                            "fine_tuned_score": fine_tuned_score,
                            "reason": "API仅返回推理内容，已提取评分",
                        },
                        ensure_ascii=False,
                    )
                    return extracted, None, debug_attempts

            print(f"{purpose} 第 {attempt}/{JUDGE_RETRIES} 次未返回可解析评分，正在重试。")
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            debug_attempts.append(
                {
                    "attempt": attempt,
                    "error": str(exc),
                }
            )
            print(f"{purpose} 第 {attempt}/{JUDGE_RETRIES} 次失败: {exc}")

        if attempt < JUDGE_RETRIES:
            time.sleep(2 ** (attempt - 1))

    return None, "API未返回可解析评分，已使用本地保底评分", debug_attempts


def auto_evaluate(api_config=None):
    """Evaluate answers using the selected API."""
    api_config = get_api_config() if api_config is None else ensure_api_config(api_config)
    loaded = _load_answers()
    if loaded is None:
        return False

    questions, original_answers, fine_tuned_answers = loaded
    print(f"开始使用 {api_config.provider} API 自动评估 {len(questions)} 个问题的回答")

    results = []
    debug_records = []
    for i, (question, original_answer, fine_tuned_answer) in enumerate(zip(questions, original_answers, fine_tuned_answers), 1):
        print(f"\n评估问题 {i}: {question[:50]}...")
        print(f"中间过程: 原始答案长度={len(original_answer)}，微调答案长度={len(fine_tuned_answer)}")
        pair = [
            ("original", original_answer),
            ("fine_tuned", fine_tuned_answer),
        ]
        random.shuffle(pair)
        answer_a_id, answer_a = pair[0]
        answer_b_id, answer_b = pair[1]
        print(f"中间过程: 盲评映射 A={_model_label(answer_a_id)}，B={_model_label(answer_b_id)}")
        content, fallback_note, judge_attempts = _request_judge(
            api_config,
            _build_evaluation_prompt(question, answer_a, answer_b),
            f"评估问题 {i}",
        )

        if content:
            answer_a_score, answer_b_score, reason = _parse_score(content)
        else:
            answer_a_score, answer_b_score, reason = None, None, ""
        print(f"中间过程: API原始评分内容={repr((content or '')[:300])}")
        print(f"中间过程: 解析后 A={answer_a_score}，B={answer_b_score}")

        if answer_a_score is None or answer_b_score is None:
            answer_a_score = _fallback_score(answer_a)
            answer_b_score = _fallback_score(answer_b)
            reason = fallback_note or "API评分解析失败，已使用本地保底评分"

        scores = {
            answer_a_id: answer_a_score,
            answer_b_id: answer_b_score,
        }
        original_score = scores["original"]
        fine_tuned_score = scores["fine_tuned"]
        reason = _format_blind_reason(reason, answer_a_id, answer_b_id)
        print(f"原始模型: {original_score:.2f}，微调模型: {fine_tuned_score:.2f}，理由: {reason}")
        debug_records.append(
            {
                "index": i,
                "question": question,
                "answer_lengths": {
                    "original": len(original_answer),
                    "fine_tuned": len(fine_tuned_answer),
                    "answer_a": len(answer_a),
                    "answer_b": len(answer_b),
                },
                "blind_mapping": {
                    "answer_a": answer_a_id,
                    "answer_b": answer_b_id,
                },
                "answer_preview": {
                    "original": original_answer[:500],
                    "fine_tuned": fine_tuned_answer[:500],
                    "answer_a": answer_a[:500],
                    "answer_b": answer_b[:500],
                },
                "judge_content": content,
                "judge_attempts": judge_attempts,
                "parsed_scores": {
                    "answer_a": answer_a_score,
                    "answer_b": answer_b_score,
                    "original": original_score,
                    "fine_tuned": fine_tuned_score,
                },
                "reason": reason,
            }
        )
        results.append(
            {
                "question": question,
                "original_answer": original_answer,
                "fine_tuned_answer": fine_tuned_answer,
                "blind_answer_a": answer_a_id,
                "blind_answer_b": answer_b_id,
                "original_score": original_score,
                "fine_tuned_score": fine_tuned_score,
                "evaluation": reason,
            }
        )

    if not results:
        print("没有可评估结果，已停止。")
        return False

    original_total = sum(r["original_score"] for r in results)
    fine_tuned_total = sum(r["fine_tuned_score"] for r in results)
    _save_evaluation(results, original_total, fine_tuned_total)
    with open(EVALUATION_DEBUG_FILE, "w", encoding="utf-8") as f:
        json.dump(debug_records, f, ensure_ascii=False, indent=2)
    print(f"评估调试过程已保存到 {EVALUATION_DEBUG_FILE}")
    return True


def main():
    """Main entry."""
    print("请选择评估方式:")
    print("1. 人工盲评")
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
