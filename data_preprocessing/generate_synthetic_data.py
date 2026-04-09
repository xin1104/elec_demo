import json
import random
from datetime import datetime, timedelta

# 电力设备类型
equipment_types = ["变压器", "断路器", "隔离开关", "互感器", "避雷器", "电容器", "电抗器", "电缆", "母线", "绝缘子"]

# 设备状态
equipment_status = ["正常", "异常", "缺陷", "故障"]

# 运检任务类型
task_types = ["例行巡检", "定期维护", "故障处理", "状态检修", "预防性试验"]

# 故障类型
fault_types = ["过热", "放电", "绝缘损坏", "机械故障", "老化", "受潮", "过载", "短路"]

# 处理措施
treatment_measures = ["更换部件", "清理维护", "加强监测", "调整参数", "检修试验", "退役更换"]

# 生成模拟数据
def generate_synthetic_data(num_records=1000):
    data = []
    start_date = datetime(2024, 1, 1)
    
    for i in range(num_records):
        record_date = start_date + timedelta(days=random.randint(0, 365))
        equipment_type = random.choice(equipment_types)
        equipment_id = f"{equipment_type[:2]}{random.randint(1000, 9999)}"
        status = random.choice(equipment_status)
        task_type = random.choice(task_types)
        
        # 根据状态生成不同的内容
        if status == "正常":
            content = f"{record_date.strftime('%Y-%m-%d')}，{equipment_type}（编号：{equipment_id}）进行{task_type}，各项指标正常，运行状态良好。"
        else:
            fault_type = random.choice(fault_types)
            treatment = random.choice(treatment_measures)
            content = f"{record_date.strftime('%Y-%m-%d')}，{equipment_type}（编号：{equipment_id}）进行{task_type}时发现{status}，具体为{fault_type}，采取{treatment}措施后恢复正常。"
        
        data.append({
            "id": i + 1,
            "date": record_date.strftime('%Y-%m-%d'),
            "equipment_type": equipment_type,
            "equipment_id": equipment_id,
            "status": status,
            "task_type": task_type,
            "content": content
        })
    
    return data

# 保存数据到文件
def save_data(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"模拟数据已生成并保存到 {output_file}")

if __name__ == "__main__":
    synthetic_data = generate_synthetic_data(1000)
    save_data(synthetic_data, "demo_system/data/synthetic_power_inspection_data.json")
