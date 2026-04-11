# 大模型调优验证适配项目

## 项目概述

本项目旨在为电力运检场景提供大模型调优验证适配服务，包括大模型基座运检场景应用优化试验、面向电力运检的大模型压缩实施验证、面向电力运检的大模型应用环境适配运行。

## 目录结构

```
demo_system/
├── clean/            # 数据处理模块
│   ├── data_processor.py  # 数据处理脚本
│   └── requirements.txt    # 依赖文件
├── crawl/            # 爬虫模块
│   ├── electricity_crawler.py  # 电力资料爬虫
│   └── requirements.txt        # 依赖文件
├── data/             # 数据目录
│   └── ...           # 电力相关文本资料
├── LlamaFactory/     # 大模型微调框架
└── README.md         # 项目说明文档
```

## 安装方法

### 1. 环境准备

确保您的系统已安装Python 3.8或更高版本。

### 2. 安装依赖

#### 数据处理模块依赖

```bash
cd demo_system/clean
pip install -r requirements.txt
```

#### 爬虫模块依赖

```bash
cd demo_system/crawl
pip install -r requirements.txt
```

#### LlamaFactory依赖

```bash
cd demo_system/LlamaFactory
pip install -e .
pip install -r requirements/metrics.txt
```

## 使用方法

### 1. 数据收集

#### 方法一：使用爬虫收集数据

```bash
cd demo_system/crawl
python electricity_crawler.py
```

爬虫会自动爬取电力相关网站的文章内容，并保存到`demo_system/data`目录。

#### 方法二：手动添加数据

将电力相关的文本资料保存到`demo_system/data`目录，格式为.txt文件。

### 2. 数据处理

运行数据处理脚本，将文本资料转换为大模型微调所需的QA问答对格式：

```bash
cd demo_system/clean
python data_processor.py
```

运行时需要输入DeepSeek API密钥，脚本会自动处理`demo_system/data`目录中的文本文件，生成QA问答对并保存到`processed_qa_pairs.json`文件。

### 3. 模型微调

使用LlamaFactory框架对大模型进行微调：

```bash
cd demo_system/LlamaFactory
python train.py --config configs/train_config.yaml
```

### 4. 模型压缩

对微调后的模型进行压缩：

```bash
cd demo_system/LlamaFactory
python train.py --config configs/compress_config.yaml
```

### 5. 模型部署

将压缩后的模型部署到生产环境：

```bash
cd demo_system/LlamaFactory
python api.py --model_name_or_path outputs/qwen3.5-finetuned
```

## 配置说明

### 数据处理配置

在`demo_system/clean/data_processor.py`中，您可以修改以下参数：

- `data_dir`：数据目录路径
- `output_file`：输出文件路径
- `max_tokens`：API请求的最大令牌数
- `temperature`：生成文本的温度参数

### 模型微调配置

在`demo_system/LlamaFactory/configs/train_config.yaml`中，您可以修改以下参数：

- `model_name_or_path`：预训练模型路径
- `data_path`：训练数据路径
- `output_dir`：输出目录
- `learning_rate`：学习率
- `num_train_epochs`：训练轮次
- `per_device_train_batch_size`：批量大小

## 注意事项

1. 使用DeepSeek API需要申请API密钥
2. 爬虫运行可能会受到网站反爬机制的限制
3. 模型微调需要足够的GPU资源
4. 请确保数据符合相关法律法规要求

## 联系方式

如有问题，请联系项目负责人。