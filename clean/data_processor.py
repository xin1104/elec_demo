import json
import os
import argparse
import re
import shutil
import sys
import time
from typing import Any

import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_options import ApiConfig, ensure_api_config, prompt_api_config


CHUNK_SIZE = 6000
CHUNK_OVERLAP = 500
MIN_OUTPUT_CHARS = 260
MAX_OUTPUT_CHARS = 900
MAX_QA_PER_CHUNK = 8
REQUEST_RETRIES = 3

DANGEROUS_PATTERNS = [
    "用手触摸风扇叶片",
    "先验电、后合闸",
    "验电后合闸",
    "带负荷拉合隔离开关",
    "未验电直接装设接地线",
    "未停电直接检修",
    "每日清扫绝缘子",
    "动平衡试验",
    "转子是否平衡",
]

NEGATION_WORDS = ["严禁", "禁止", "不得", "不能", "避免", "防止", "不应", "切勿", "杜绝"]

QUALITY_TERMS = [
    "检查",
    "判断",
    "步骤",
    "风险",
    "安全",
    "措施",
    "处置",
    "记录",
    "复核",
    "验电",
    "接地",
    "隔离",
    "监护",
    "缺陷",
    "标准",
    "规程",
]


class DataProcessor:
    def __init__(self, data_dir: str, output_file: str):
        self.clean_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.clean_dir)
        self.data_dir = data_dir if os.path.isabs(data_dir) else os.path.join(self.project_root, data_dir)
        self.output_file = output_file if os.path.isabs(output_file) else os.path.join(self.clean_dir, output_file)
        self.llamafactory_data_file = os.path.join(
            self.project_root, "LlamaFactory", "data", os.path.basename(self.output_file)
        )
        self.processed_files_file = os.path.join(self.clean_dir, "processed_files.json")
        self.api_config: ApiConfig | None = None

    def set_api_key(self, api_key: str):
        self.api_config = ensure_api_config(api_key)

    def set_api_config(self, api_config: ApiConfig):
        self.api_config = api_config

    def get_processed_files(self) -> set[str]:
        if os.path.exists(self.processed_files_file):
            try:
                with open(self.processed_files_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return set(json.loads(content)) if content else set()
            except (json.JSONDecodeError, OSError) as exc:
                print(f"读取已处理文件列表失败，将重新创建: {exc}")
                return set()
        return set()

    def save_processed_files(self, processed_files: set[str]):
        with open(self.processed_files_file, "w", encoding="utf-8") as f:
            json.dump(sorted(processed_files), f, ensure_ascii=False, indent=2)

    def get_all_text_files(self) -> list[str]:
        if not os.path.isdir(self.data_dir):
            raise FileNotFoundError(f"数据目录不存在: {self.data_dir}")

        return sorted(filename for filename in os.listdir(self.data_dir) if filename.endswith(".txt"))

    def get_new_files(self) -> list[str]:
        processed_files = self.get_processed_files()
        return [filename for filename in self.get_all_text_files() if filename not in processed_files]

    def read_file(self, filename: str) -> str:
        file_path = os.path.join(self.data_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def split_text(self, text: str) -> list[str]:
        text = re.sub(r"\n{3,}", "\n\n", text.strip())
        if len(text) <= CHUNK_SIZE:
            return [text] if text else []

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            if end < len(text):
                paragraph_break = text.rfind("\n\n", start + CHUNK_SIZE // 2, end)
                if paragraph_break > start:
                    end = paragraph_break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break
            start = max(0, end - CHUNK_OVERLAP)

        return chunks

    def build_generation_prompt(self, text: str, filename: str, chunk_index: int, chunk_count: int) -> str:
        return f"""请根据下面的电力运检资料，生成用于微调模型的高质量 instruction/output 问答数据。

资料来源：{filename}，分块：{chunk_index}/{chunk_count}

资料内容：
{text}

生成目标：
1. 本批生成 5 到 {MAX_QA_PER_CHUNK} 条高质量 QA，质量优先，不要灌水。
2. 重点生成现场流程型、风险研判型、故障处置型、标准化作业型问题，少生成纯概念定义题。
3. 每个 instruction 必须是具体场景问题，避免“是什么/有什么意义”这类过短泛问。
4. 每个 output 控制在 300-650 个中文字符，使用分点结构。
5. 每个 output 至少覆盖：判断/检查要点、关键操作步骤、主要风险点、安全控制措施或后续处置。
6. 涉及阈值、周期、标准编号时，只能使用资料中明确出现的内容；资料没有明确数值时，写“按现行规程或现场标准执行”，不要编造。
7. 严禁危险建议，例如带负荷拉合隔离开关、未验电装设接地线、未停电直接检修、用手触摸运行设备等。
8. 避免机械重复，禁止输出同一句话或同一短语连续重复。
9. 每条数据只允许包含 instruction 和 output 两个字段。
10. 只返回 JSON，不要 Markdown，不要解释。格式如下：
{{
  "qa_pairs": [
    {{
      "instruction": "具体场景问题",
      "output": "结构化、专业、可执行的回答"
    }}
  ]
}}
"""

    def call_api(self, prompt: str, purpose: str) -> str | None:
        if not self.api_config:
            raise ValueError("请先设置 API 配置")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_config.api_key}",
        }
        payload: dict[str, Any] = {
            "model": self.api_config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是电力运检资料标注专家，只输出可解析 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
            "max_tokens": 5000,
            "response_format": {"type": "json_object"},
        }

        if self.api_config.provider == "Xiaomi MiMo":
            payload["enable_thinking"] = False
            payload["thinking_budget"] = 0

        for attempt in range(1, REQUEST_RETRIES + 1):
            try:
                response = requests.post(self.api_config.api_url, headers=headers, json=payload, timeout=120)
                if response.status_code >= 400:
                    fallback_payload = dict(payload)
                    fallback_payload.pop("response_format", None)
                    fallback_payload.pop("enable_thinking", None)
                    fallback_payload.pop("thinking_budget", None)
                    response = requests.post(self.api_config.api_url, headers=headers, json=fallback_payload, timeout=120)

                print(f"{purpose} API 状态码: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                message = result.get("choices", [{}])[0].get("message", {})
                content = (message.get("content") or "").strip()
                if content:
                    return content

                print(f"{purpose} 第 {attempt}/{REQUEST_RETRIES} 次返回为空，准备重试。")
            except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
                print(f"{purpose} 第 {attempt}/{REQUEST_RETRIES} 次失败: {exc}")

            if attempt < REQUEST_RETRIES:
                time.sleep(2 ** (attempt - 1))

        return None

    def parse_qa_content(self, content: str) -> list[dict[str, str]]:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:].strip()
        elif content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            content = match.group(0)

        data = json.loads(content)
        if isinstance(data, list):
            raw_pairs = data
        else:
            raw_pairs = data.get("qa_pairs") or data.get("data") or data.get("items") or []

        pairs = []
        for item in raw_pairs:
            if not isinstance(item, dict):
                continue
            instruction = str(item.get("instruction", "")).strip()
            output = str(item.get("output", "")).strip()
            pairs.append({"instruction": instruction, "output": output})

        return pairs

    def has_repetition(self, text: str) -> bool:
        if re.search(r"(.{4,24})\1{3,}", text):
            return True

        phrases = re.findall(r"[\u4e00-\u9fff]{4,12}", text)
        seen: dict[str, int] = {}
        for phrase in phrases:
            seen[phrase] = seen.get(phrase, 0) + 1
            if seen[phrase] >= 8:
                return True

        return False

    def has_dangerous_advice(self, text: str) -> bool:
        for pattern in DANGEROUS_PATTERNS:
            start = 0
            while True:
                index = text.find(pattern, start)
                if index == -1:
                    break
                prefix = text[max(0, index - 12) : index]
                if not any(word in prefix for word in NEGATION_WORDS):
                    return True
                start = index + len(pattern)
        return False

    def quality_reason(self, pair: dict[str, str]) -> str | None:
        instruction = pair.get("instruction", "").strip()
        output = pair.get("output", "").strip()

        if not instruction or not output:
            return "字段为空"
        if len(instruction) < 12:
            return "问题过短"
        if len(output) < MIN_OUTPUT_CHARS:
            return f"回答过短({len(output)}字)"
        if len(output) > MAX_OUTPUT_CHARS:
            return f"回答过长({len(output)}字)"
        if self.has_dangerous_advice(output):
            return "包含危险或明显错误表述"
        if self.has_repetition(output):
            return "存在重复退化"

        term_hits = sum(1 for term in QUALITY_TERMS if term in output)
        if term_hits < 4:
            return "缺少现场作业要素"

        if not re.search(r"(1[.、]|一、|（一）|首先|其次|最后)", output):
            return "缺少结构化步骤"

        return None

    def filter_qa_pairs(self, qa_pairs: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
        valid_pairs = []
        rejected_reasons = []
        seen_instructions = set()

        for pair in qa_pairs:
            pair = {
                "instruction": re.sub(r"\s+", " ", pair.get("instruction", "")).strip(),
                "output": re.sub(r"\n{3,}", "\n\n", pair.get("output", "")).strip(),
            }
            reason = self.quality_reason(pair)
            if reason:
                rejected_reasons.append(reason)
                continue

            key = pair["instruction"]
            if key in seen_instructions:
                rejected_reasons.append("问题重复")
                continue

            seen_instructions.add(key)
            valid_pairs.append(pair)

        return valid_pairs, rejected_reasons

    def generate_qa_pairs(self, text: str, filename: str = "") -> list[dict[str, str]]:
        chunks = self.split_text(text)
        all_pairs: list[dict[str, str]] = []
        rejected: list[str] = []

        for index, chunk in enumerate(chunks, 1):
            prompt = self.build_generation_prompt(chunk, filename or "unknown", index, len(chunks))
            content = self.call_api(prompt, f"{filename} 分块 {index}/{len(chunks)}")
            if not content:
                print(f"{filename} 分块 {index} 未生成有效内容，跳过。")
                continue

            try:
                parsed_pairs = self.parse_qa_content(content)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                print(f"{filename} 分块 {index} JSON 解析失败: {exc}")
                print(f"响应片段: {content[:500]}")
                continue

            valid_pairs, rejected_reasons = self.filter_qa_pairs(parsed_pairs)
            all_pairs.extend(valid_pairs)
            rejected.extend(rejected_reasons)
            print(
                f"{filename} 分块 {index}: 解析 {len(parsed_pairs)} 条，"
                f"保留 {len(valid_pairs)} 条，过滤 {len(rejected_reasons)} 条"
            )

        if rejected:
            summary: dict[str, int] = {}
            for reason in rejected:
                summary[reason] = summary.get(reason, 0) + 1
            print(f"{filename} 过滤原因统计: {summary}")

        return all_pairs

    def load_existing_qa_pairs(self) -> list[dict[str, str]]:
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return json.loads(content) if content else []
            except (json.JSONDecodeError, OSError) as exc:
                print(f"读取已有问答对失败，将创建新文件: {exc}")
                return []
        return []

    def dedupe_qa_pairs(self, qa_pairs: list[dict[str, str]]) -> list[dict[str, str]]:
        deduped = []
        seen = set()
        for pair in qa_pairs:
            key = pair.get("instruction", "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(pair)
        return deduped

    def save_qa_pairs(self, qa_pairs: list[dict[str, str]]):
        qa_pairs = self.dedupe_qa_pairs(qa_pairs)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
        self.print_dataset_stats(qa_pairs)

    def print_dataset_stats(self, qa_pairs: list[dict[str, str]]):
        if not qa_pairs:
            print("当前数据集为空。")
            return

        lengths = sorted(len(pair.get("output", "")) for pair in qa_pairs)
        mid = len(lengths) // 2
        median = lengths[mid] if len(lengths) % 2 else (lengths[mid - 1] + lengths[mid]) / 2
        short_count = sum(length < MIN_OUTPUT_CHARS for length in lengths)
        print(
            "数据集统计: "
            f"总数={len(qa_pairs)}, "
            f"回答中位数={median:.1f}字, "
            f"最短={lengths[0]}字, 最长={lengths[-1]}字, "
            f"低于{MIN_OUTPUT_CHARS}字={short_count}条"
        )
        if len(qa_pairs) < 300:
            print("提醒: 当前 QA 数量少于 300 条，通常不足以稳定提升复杂流程题表现。")

    def sync_to_llamafactory(self):
        if not os.path.exists(self.output_file):
            print(f"输出文件不存在，跳过同步: {self.output_file}")
            return

        os.makedirs(os.path.dirname(self.llamafactory_data_file), exist_ok=True)
        shutil.copy2(self.output_file, self.llamafactory_data_file)
        print(f"已同步到 LlamaFactory: {self.llamafactory_data_file}")

    def process(self, rebuild: bool = False):
        print("检查新增文件...")
        new_files = self.get_all_text_files() if rebuild else self.get_new_files()

        if not new_files:
            print("没有发现新增文件")
            self.sync_to_llamafactory()
            return True

        if rebuild:
            print(f"重建模式：将重新处理 {len(new_files)} 个文本文件，并覆盖原有 QA 数据。")
            existing_qa_pairs = []
            processed_files = set()
        else:
            print(f"发现 {len(new_files)} 个新增文件")
            existing_qa_pairs = self.load_existing_qa_pairs()
            processed_files = self.get_processed_files()

        for filename in new_files:
            print(f"\n处理文件: {filename}")
            text = self.read_file(filename)
            print(f"读取 {len(text)} 字符，开始生成 QA...")
            qa_pairs = self.generate_qa_pairs(text, filename)

            if not qa_pairs:
                print(f"{filename} 没有生成通过质量检查的 QA，暂不标记为已处理。")
                continue

            existing_qa_pairs.extend(qa_pairs)
            existing_qa_pairs = self.dedupe_qa_pairs(existing_qa_pairs)
            self.save_qa_pairs(existing_qa_pairs)

            processed_files.add(filename)
            self.save_processed_files(processed_files)
            print(f"{filename} 处理完成，新增有效 QA {len(qa_pairs)} 条")

        self.sync_to_llamafactory()
        print(f"处理完成，结果保存在 {self.output_file}")
        return True


def parse_args():
    parser = argparse.ArgumentParser(description="Generate high-quality QA pairs for LlamaFactory fine-tuning.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="重新处理 data/*.txt，并覆盖 clean/processed_qa_pairs.json 与 processed_files.json。",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    processor = DataProcessor(data_dir="data", output_file="processed_qa_pairs.json")
    api_config = prompt_api_config()
    processor.set_api_config(api_config)
    processor.process(rebuild=args.rebuild)
