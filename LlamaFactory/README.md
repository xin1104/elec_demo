# LLaMA Factory

Unified Efficient Fine-Tuning of 100+ LLMs

## Overview

LLaMA Factory is a unified framework for fine-tuning large language models (LLMs). It supports various fine-tuning methods including supervised fine-tuning (SFT), reward modeling (RM), direct preference optimization (DPO), and more.

## Features

- Support for 100+ LLMs including Llama 3, Qwen, Mistral, DeepSeek, and more
- Multiple fine-tuning methods: SFT, RM, DPO, PPO, KTO, etc.
- Efficient training with PEFT methods (LoRA, QLoRA, etc.)
- Support for multimodal models
- Web UI for easy configuration and monitoring
- REST API for model serving

## Installation

```bash
# Install from source
pip install -e .

# Install additional dependencies
pip install -r requirements/metrics.txt
```

## Usage

### Training

```bash
# Supervised fine-tuning
python train.py --config configs/train_config.yaml

# DPO training
python train.py --config configs/dpo_config.yaml
```

### Inference

```bash
# Start API server
python api.py --model_name_or_path outputs/model

# Start Web UI
python webui.py
```

## Documentation

Please refer to the [GitHub repository](https://github.com/hiyouga/LLaMA-Factory) for detailed documentation.
