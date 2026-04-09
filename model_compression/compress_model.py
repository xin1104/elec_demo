import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
import time
import os

# 加载原始模型
def load_original_model(model_path="./trained_model"):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path)
    return tokenizer, model

# 计算模型大小
def get_model_size(model):
    torch.save(model.state_dict(), "temp_model.pt")
    size = os.path.getsize("temp_model.pt") / (1024 * 1024)
    os.remove("temp_model.pt")
    return size

# 量化模型
def quantize_model(model):
    # 动态量化
    quantized_model = torch.quantization.quantize_dynamic(
        model,
        {torch.nn.Linear},
        dtype=torch.qint8
    )
    return quantized_model

# 使用LoRA进行参数高效微调
def apply_lora(model):
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.1,
        bias="none"
    )
    lora_model = get_peft_model(model, lora_config)
    return lora_model

# 测试模型推理速度
def test_inference_speed(model, tokenizer, test_text="电力设备运检记录：变压器（编号：变1234）进行例行巡检，各项指标正常，运行状态良好。"):
    inputs = tokenizer(test_text, return_tensors="pt")
    
    start_time = time.time()
    with torch.no_grad():
        outputs = model(**inputs)
    end_time = time.time()
    
    inference_time = end_time - start_time
    return inference_time

# 压缩模型
def compress_model():
    # 加载原始模型
    tokenizer, original_model = load_original_model()
    
    # 计算原始模型大小
    original_size = get_model_size(original_model)
    print(f"原始模型大小: {original_size:.2f} MB")
    
    # 测试原始模型推理速度
    original_speed = test_inference_speed(original_model, tokenizer)
    print(f"原始模型推理速度: {original_speed:.4f} 秒")
    
    # 应用量化
    quantized_model = quantize_model(original_model)
    quantized_size = get_model_size(quantized_model)
    print(f"量化后模型大小: {quantized_size:.2f} MB")
    
    # 测试量化模型推理速度
    quantized_speed = test_inference_speed(quantized_model, tokenizer)
    print(f"量化后模型推理速度: {quantized_speed:.4f} 秒")
    
    # 应用LoRA
    lora_model = apply_lora(original_model)
    lora_size = get_model_size(lora_model)
    print(f"LoRA后模型大小: {lora_size:.2f} MB")
    
    # 测试LoRA模型推理速度
    lora_speed = test_inference_speed(lora_model, tokenizer)
    print(f"LoRA后模型推理速度: {lora_speed:.4f} 秒")
    
    # 保存压缩后的模型
    lora_model.save_pretrained("./compressed_model")
    tokenizer.save_pretrained("./compressed_model")
    
    print("模型压缩完成并保存到 ./compressed_model")
    
    # 生成压缩报告
    report = {
        "original_model": {
            "size_mb": original_size,
            "inference_time_seconds": original_speed
        },
        "quantized_model": {
            "size_mb": quantized_size,
            "inference_time_seconds": quantized_speed
        },
        "lora_model": {
            "size_mb": lora_size,
            "inference_time_seconds": lora_speed
        }
    }
    
    with open("./compression_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("压缩报告已生成: ./compression_report.json")

if __name__ == "__main__":
    compress_model()
