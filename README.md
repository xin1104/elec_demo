# 电力运检大模型调优验证项目

本项目用于构建电力运检领域文本资料、生成微调问答数据，并基于 LlamaFactory 完成模型微调与效果评估。当前流程支持通过控制台选择 API 服务商与模型，可使用 DeepSeek API 或小米 MiMo OpenAI 兼容接口来生成资料、生成评测问题和自动评估回答。

## 目录结构

```text
├── api_options.py                       # API 服务商、模型选择与请求地址配置
├── clean/
│   ├── data_processor.py                # 将 data/*.txt 转换为 QA 问答对
│   ├── processed_files.json             # 已处理文本文件记录
│   └── processed_qa_pairs.json          # 生成的 QA 数据
├── crawl/
│   ├── electricity_crawler.py           # 电力资料爬虫（实验性质）
│   └── visited_urls.json                # 爬虫访问记录
├── data/
│   ├── generate_electricity_docs.py     # 批量生成电力资料文本
│   └── *.txt                            # 电力运检原始文本资料
├── eval/
│   ├── config.py                        # 评估相关路径与参数
│   ├── generate_questions.py            # 生成评测问题
│   ├── get_model_answers.py             # 获取训练前/训练后模型回答
│   ├── evaluate_answers.py              # 人工或 API 自动评分
│   └── run_evaluation.py                # 评估主菜单
├── LlamaFactory/                        # 本地 LlamaFactory 微调框架
├── requirements.txt                     # Python 依赖
└── README.md
```

## 环境安装

建议使用 Python 3.11，并在项目根目录创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

`requirements.txt` 已使用本地 LlamaFactory：

```text
-e ./LlamaFactory
-r LlamaFactory/requirements/metrics.txt
```

如果你的显卡、CUDA 或 PyTorch 版本有特殊要求，请按本机环境单独调整 `torch`、`torchvision`、`torchaudio` 版本。

## API 选择

以下脚本会在控制台先让你选择 API 服务商，再选择具体模型，最后输入对应 API key：

- `data/generate_electricity_docs.py`
- `clean/data_processor.py`
- `eval/generate_questions.py`
- `eval/evaluate_answers.py`
- `eval/run_evaluation.py`

当前内置服务商：

- DeepSeek：`https://api.deepseek.com/v1`
- Xiaomi MiMo：`https://token-plan-cn.xiaomimimo.com/v1`

小米 MiMo 使用 OpenAI 兼容的 `/chat/completions` 接口。当前菜单仅保留文本相关模型 ID：`mimo-v2.5-pro`、`mimo-v2.5`、`mimo-v2-pro`、`mimo-v2-omni`。

## 使用流程

### 1. 准备电力资料

方式一：批量生成资料（推荐）。

```powershell
python data/generate_electricity_docs.py
```

脚本会提示输入生成数量，并在 `data/` 下生成 `AI生成_*.txt` 文件。提示词会轮换生成运维规程、故障分析、培训资料、技术论文、应急预案、设备手册、巡检纪要等类型，文本长度不会太短，尽量贴近真实电力运检资料。

方式二：手动添加资料。

将电力相关文本保存到 `data/` 目录，文件扩展名使用 `.txt`。

方式三：爬虫收集资料（实验性质）。

```powershell
python crawl/electricity_crawler.py
```

爬虫可能受到目标站点结构变化或反爬限制影响，建议优先使用批量生成或手动整理资料。

### 2. 生成 QA 问答数据

```powershell
python clean/data_processor.py
```

脚本只会扫描 `data/` 下的 `.txt` 文件，不会读取 `data/generate_electricity_docs.py`。已处理文件会记录在 `clean/processed_files.json`，生成结果保存到 `clean/processed_qa_pairs.json`。

### 3. 模型微调

命令行训练：

```powershell
python LlamaFactory/src/train.py --config LlamaFactory/examples/train_lora/qwen3_5_0_8b_lora_sft.yaml
```

Web UI（推荐）：

```powershell
python LlamaFactory/src/webui.py
```

启动后访问：

```text
http://127.0.0.1:7860
```

微调配置位于 `LlamaFactory/examples/train_lora/qwen3_5_0_8b_lora_sft.yaml`，可调整模型路径、数据集、训练轮次、batch size、学习率、LoRA rank、LoRA alpha 等参数。

### 4. 模型效果评估

运行评估主菜单：

```powershell
python eval/run_evaluation.py
```

菜单说明：

1. 生成电力运检领域专业问题
2. 获取模型回答
3. 评估模型回答
4. 运行完整评估流程
0. 退出

评估配置在 `eval/config.py` 中，包括训练前模型路径、LoRA 路径、问题数量、输出文件名等。自动评估会调用你在控制台选择的 API 模型，对训练前后回答进行评分并保存到 `eval/evaluation_results.json`。

## 常用文件说明

- `api_options.py`：统一维护服务商、模型列表、base URL 与控制台选择逻辑。
- `data/generate_electricity_docs.py`：生成原始电力资料文本，只创建 `.txt`，不会影响其它脚本本身的加载。
- `clean/data_processor.py`：读取 `data/*.txt`，调用所选 API 生成 instruction/output 格式 QA。
- `eval/run_evaluation.py`：评估流程入口，完整流程中只选择一次 API，生成问题和自动评分会复用同一配置。
- `requirements.txt`：使用本地 LlamaFactory，避免从远端 git 子目录安装时出现 README 缺失等构建问题。

## 注意事项

1. 请妥善保管 API key，不要提交到仓库。
2. AI 生成资料只适合实验和数据构造，正式业务场景应由专业人员复核。
3. 如果重新生成或替换了 `data/*.txt`，需要留意 `clean/processed_files.json`，已记录的同名文件不会重复处理。
4. 模型微调需要足够 GPU 资源，显存不足时可降低 batch size、启用更小模型或使用 LoRA/量化配置。
5. 爬虫模块为实验性质，使用时请遵守目标网站规则和相关法律法规。
