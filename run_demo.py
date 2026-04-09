import os
import subprocess
import time

def run_command(command, cwd=None):
    """运行命令并返回结果"""
    print(f"执行命令: {command}")
    result = subprocess.run(
        command, 
        shell=True, 
        capture_output=True, 
        text=True, 
        cwd=cwd
    )
    print(f"命令输出: {result.stdout}")
    if result.stderr:
        print(f"命令错误: {result.stderr}")
    return result

def main():
    print("===== 电力运检大模型调优验证适配Demo =====")
    print("1. 安装依赖包")
    run_command("pip install -r requirements.txt")
    
    print("\n2. 生成模拟数据")
    run_command("python data_preprocessing/generate_synthetic_data.py")
    
    print("\n3. 训练模型")
    run_command("python model_training/train_model.py")
    
    print("\n4. 压缩模型")
    run_command("python model_compression/compress_model.py")
    
    print("\n5. 启动API服务")
    print("服务将在 http://localhost:8000 启动")
    print("API文档地址: http://localhost:8000/docs")
    print("健康检查地址: http://localhost:8000/health")
    print("模型推理地址: http://localhost:8000/predict")
    print("模型信息地址: http://localhost:8000/model/info")
    
    # 启动服务
    process = subprocess.Popen(
        "python deployment/app.py", 
        shell=True,
        cwd="."
    )
    
    # 等待服务启动
    time.sleep(5)
    
    print("\n6. 测试API服务")
    test_command = "curl -X POST http://localhost:8000/predict -H \"Content-Type: application/json\" -d '{\"text\": \"电力设备运检记录：变压器（编号：变1234）进行例行巡检，\"}'"
    run_command(test_command)
    
    print("\n===== Demo运行完成 =====")
    print("服务正在运行中，按 Ctrl+C 停止服务")
    
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        print("服务已停止")

if __name__ == "__main__":
    main()
