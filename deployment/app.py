from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import uvicorn

# 初始化FastAPI应用
app = FastAPI(title="电力运检大模型API")

# 加载模型和分词器
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    try:
        # 优先加载压缩模型
        tokenizer = AutoTokenizer.from_pretrained("./compressed_model")
        model = AutoModelForCausalLM.from_pretrained("./compressed_model")
        print("压缩模型加载成功")
    except:
        # 如果压缩模型不存在，加载原始模型
        tokenizer = AutoTokenizer.from_pretrained("./trained_model")
        model = AutoModelForCausalLM.from_pretrained("./trained_model")
        print("原始模型加载成功")

# 启动时加载模型
@app.on_event("startup")
async def startup_event():
    load_model()

# 请求模型
class ModelRequest(BaseModel):
    text: str
    max_length: int = 512

# 响应模型
class ModelResponse(BaseModel):
    generated_text: str
    inference_time: float

# 健康检查接口
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "电力运检大模型服务运行正常"}

# 模型推理接口
@app.post("/predict", response_model=ModelResponse)
async def predict(request: ModelRequest):
    if not tokenizer or not model:
        raise HTTPException(status_code=500, detail="模型未加载")
    
    try:
        # 处理输入
        inputs = tokenizer(request.text, return_tensors="pt")
        
        # 推理
        import time
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=request.max_length,
                num_return_sequences=1,
                no_repeat_ngram_size=2,
                early_stopping=True
            )
        end_time = time.time()
        
        # 解码输出
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 计算推理时间
        inference_time = end_time - start_time
        
        return ModelResponse(
            generated_text=generated_text,
            inference_time=inference_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 模型信息接口
@app.get("/model/info")
async def model_info():
    return {
        "model_name": "电力运检大模型",
        "base_model": "Qwen/Qwen2-0.5B",
        "status": "已加载" if model else "未加载"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
