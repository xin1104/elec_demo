# 大模型调优验证适配项目

## 项目概述

本项目旨在为电力运检场景提供大模型调优验证适配服务，包括大模型基座运检场景应用优化试验、面向电力运检的大模型压缩实施验证、面向电力运检的大模型应用环境适配运行。

## 目录结构

```
├── clean/            # 数据处理模块
│   ├── data_processor.py  # 数据处理脚本
│   ├── processed_files.json  # 处理文件记录
│   └── processed_qa_pairs.json  # 生成的问答对数据
├── crawl/            # 爬虫模块
│   ├── electricity_crawler.py  # 电力资料爬虫
│   └── visited_urls.json        # 已访问URL记录
├── data/             # 数据目录
│   └── ...           # 电力相关文本资料
├── eval/             # 模型评估模块
│   ├── config.py     # 评估配置
│   ├── generate_questions.py  # 生成专业问题
│   ├── get_model_answers.py  # 获取模型回答
│   ├── evaluate_answers.py  # 评估模型回答
│   └── run_evaluation.py  # 评估主脚本
├── LlamaFactory/     # 大模型微调框架
├── requirements.txt  # 项目依赖
└── README.md         # 项目说明文档
```

## 安装方法

### 1. 环境准备

确保您的系统已安装Python 3.11或更高版本（LlamaFactory要求）。

### 2. 安装依赖

项目根目录下提供了统一的依赖配置文件，执行以下命令安装所有依赖：

```bash
pip install -r requirements.txt

# 安装LlamaFactory
cd LlamaFactory
pip install -e .
pip install -r requirements/metrics.txt
```

## 使用方法

### 1. 数据收集

#### 方法一：使用爬虫收集数据(目前不可用)

```bash
cd crawl
python electricity_crawler.py
```

爬虫会自动爬取电力相关网站的文章内容，并保存到`data`目录。

#### 方法二：手动添加数据

将电力相关的文本资料保存到`data`目录，格式为.txt文件。

### 2. 数据处理

运行数据处理脚本，将文本资料转换为大模型微调所需的QA问答对格式：

```bash
cd clean
python data_processor.py
```

运行时需要输入DeepSeek API密钥，脚本会自动处理`data`目录中的文本文件，生成QA问答对并保存到`processed_qa_pairs.json`文件。

### 3. 模型微调

使用LlamaFactory框架对Qwen3.5 0.8B模型进行微调：

#### 方法一：使用命令行

```bash
cd LlamaFactory
python src/train.py --config examples/train_lora/qwen3_5_0_8b_lora_sft.yaml
```

#### 方法二：使用Web UI（推荐）

```bash
cd LlamaFactory
python src/webui.py
```

然后访问 `http://127.0.0.1:7860` 进行可视化微调。

### 4. 模型压缩（待实现）

对微调后的模型进行压缩，减小模型体积，提高推理速度。

### 5. 模型部署（待实现）

将微调后的模型部署到生产环境，与业务系统对接。

## 训练结果分析

### 训练参数

- 模型：Qwen3.5 0.8B-Instruct
- 微调方法：LoRA
- 训练轮次：3
- 批量大小：4
- 学习率：1e-4
- LoRA秩：8
- LoRA Alpha：16

### 训练指标

| 指标 | 值 |
|------|-----|
| 训练轮次 | 3.0 |
| 训练样本数 | 123,920 tokens |
| 训练时间 | 5分03秒 |
| 最终损失 | 1.565 |
| 训练速度 | 2.082 样本/秒 |
| 可训练参数 | 5,411,328 (0.63%) |
| 总参数 | 858,397,248 |

### 损失曲线分析

训练损失从初始的1.9左右逐渐下降到1.4左右，整体趋势良好，说明模型正在有效学习电力运检领域的知识。

## 模型效果对比方法

### 1. 定性评估

使用Web UI与模型进行交互，对比训练前后的回答质量：

```bash
cd LlamaFactory
python src/webui.py
```

然后在Web UI中：
- **训练前的模型**：选择模型路径为 `../model/models--Qwen--Qwen3.5-0.8B-Base/snapshots/a9a407bcae463285164cc9133995c515379cebe5`
- **训练后的模型**：选择模型路径为 `../model/models--Qwen--Qwen3.5-0.8B-Base/snapshots/a9a407bcae463285164cc9133995c515379cebe5`，并选择LoRA路径为 `saves/Qwen3.5-0.8B-Base/lora/train_2026-04-12-00-04-45/checkpoint-42`

### 2. DeepSeek自动评估

使用DeepSeek API对模型回答进行自动评估：

1. **配置API密钥**：编辑 `eval/config.py` 文件，将 `DEEPSEEK_API_KEY` 替换为您的 DeepSeek API 密钥

2. **运行自动评估**：

```bash
cd eval
python run_evaluation.py
```

选择选项3，仅运行自动评估步骤（前提是已有问题和回答数据）

3. **评估方式说明**：
   - 选项 1：仅生成问题
   - 选项 2：仅获取模型回答
   - 选项 3：仅运行自动评估（需要已有问题和回答）
   - 选项 4：运行完整评估流程（一键执行）

**注意**：评估系统会使用DeepSeek-V3模型对两个模型（训练前和训练后）的回答进行盲打分，满分100分，并输出两个模型的评分结果。

## 配置说明

### 数据处理配置

在`clean/data_processor.py`中，您可以修改以下参数：

- `data_dir`：数据目录路径
- `output_file`：输出文件路径
- `max_tokens`：API请求的最大令牌数
- `temperature`：生成文本的温度参数

### 模型微调配置

在`LlamaFactory/examples/train_lora/qwen3_5_0_8b_lora_sft.yaml`中，您可以修改以下参数：

- `model_name_or_path`：预训练模型路径
- `dataset`：训练数据集名称
- `epoch`：训练轮次
- `batch_size`：批量大小
- `learning_rate`：学习率
- `lora_rank`：LoRA秩
- `lora_alpha`：LoRA Alpha值

## 注意事项

1. 使用DeepSeek API需要申请API密钥
2. 爬虫运行可能会受到网站反爬机制的限制
3. 模型微调需要足够的GPU资源（推荐至少8GB显存）
4. 请确保数据符合相关法律法规要求

## 联系方式

如有问题，请联系项目负责人。