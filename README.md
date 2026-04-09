# 电力运检大模型调优验证适配Demo

## 项目概述

本项目基于技术规范书要求，实现了大模型调优验证适配的完整流程，包括：
1. 大模型基座运检场景应用优化试验
2. 面向电力运检的大模型压缩实施验证
3. 面向电力运检的大模型应用环境适配运行

## 技术栈

- 大模型：通义千问Qwen系列（Qwen2-0.5B）
- 开发语言：Python 3.8+
- 核心库：
  - transformers：模型加载和训练
  - datasets：数据处理
  - torch：深度学习框架
  - fastapi：API服务
  - peft：参数高效微调（LoRA）

## 项目结构

```
demo_system/
├── data_preprocessing/    # 数据预处理模块
│   └── generate_synthetic_data.py  # 生成模拟数据
├── model_training/        # 模型训练模块
│   └── train_model.py     # 模型训练脚本
├── model_compression/     # 模型压缩模块
│   └── compress_model.py  # 模型压缩脚本
├── deployment/            # 环境适配模块
│   └── app.py             # API服务
├── data/                  # 数据目录
├── utils/                 # 工具函数
├── requirements.txt       # 依赖包
├── run_demo.py            # 主运行脚本
└── README.md              # 项目说明
```

## 运行说明

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行完整流程

```bash
python run_demo.py
```

该脚本会自动执行以下步骤：
1. 安装依赖包
2. 生成模拟数据
3. 训练模型
4. 压缩模型
5. 启动API服务
6. 测试API服务

### 3. 单独运行各模块

#### 生成模拟数据
```bash
python data_preprocessing/generate_synthetic_data.py
```

#### 训练模型
```bash
python model_training/train_model.py
```

#### 压缩模型
```bash
python model_compression/compress_model.py
```

#### 启动API服务
```bash
python deployment/app.py
```

## API接口

服务启动后，可通过以下接口访问：

- **健康检查**：http://localhost:8000/health
- **模型推理**：http://localhost:8000/predict
- **模型信息**：http://localhost:8000/model/info
- **API文档**：http://localhost:8000/docs

## 模型压缩

采用混合压缩方法：
1. **量化**：使用动态量化减少模型大小
2. **LoRA**：使用参数高效微调减少训练参数量

压缩前后对比会生成在 `compression_report.json` 文件中。

## 注意事项

1. 本项目使用的是Qwen2-0.5B模型，适合在本地环境运行
2. 首次运行会自动下载模型，可能需要较长时间
3. 训练过程需要一定的GPU资源（推荐至少8GB显存）
4. 若本地资源不足，可修改 `train_model.py` 中的批处理大小和模型规格
