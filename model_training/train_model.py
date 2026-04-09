import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import Dataset

# 加载数据
def load_data(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# 预处理数据
def preprocess_data(data):
    processed_data = []
    for item in data:
        # 构建训练样本
        prompt = f"电力设备运检记录：{item['content']}"
        processed_data.append({
            "text": prompt
        })
    return processed_data

# 加载模型和分词器
def load_model(model_name="Qwen/Qwen2-0.5B"):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    return tokenizer, model

# 数据分词处理
def tokenize_function(examples, tokenizer, max_length=512):
    return tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=max_length
    )

# 训练模型
def train_model():
    # 加载数据
    data = load_data("demo_system/data/synthetic_power_inspection_data.json")
    processed_data = preprocess_data(data)
    
    # 创建数据集
    dataset = Dataset.from_list(processed_data)
    
    # 加载模型和分词器
    tokenizer, model = load_model()
    
    # 分词处理
    tokenized_dataset = dataset.map(
        lambda examples: tokenize_function(examples, tokenizer),
        batched=True
    )
    
    # 划分训练集和验证集
    train_test_split = tokenized_dataset.train_test_split(test_size=0.1)
    train_dataset = train_test_split["train"]
    eval_dataset = train_test_split["test"]
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir="./results",
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        num_train_epochs=3,
        weight_decay=0.01,
        save_strategy="epoch",
        load_best_model_at_end=True
    )
    
    # 创建Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer
    )
    
    # 开始训练
    trainer.train()
    
    # 保存模型
    model.save_pretrained("./trained_model")
    tokenizer.save_pretrained("./trained_model")
    
    print("模型训练完成并保存到 ./trained_model")

if __name__ == "__main__":
    train_model()
