import os
import json
import requests
from typing import List, Dict

class DataProcessor:
    def __init__(self, data_dir: str, output_file: str):
        self.data_dir = data_dir
        self.output_file = output_file
        self.deepseek_api_key = None
        self.processed_files_file = "processed_files.json"
    
    def set_api_key(self, api_key: str):
        self.deepseek_api_key = api_key
    
    def get_processed_files(self) -> set:
        """获取已处理的文件列表"""
        if os.path.exists(self.processed_files_file):
            try:
                with open(self.processed_files_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:  # 文件为空
                        return set()
                    return set(json.loads(content))
            except (json.JSONDecodeError, Exception) as e:
                print(f"读取已处理文件列表时出错: {e}，将重新创建")
                return set()
        return set()
    
    def save_processed_files(self, processed_files: set):
        """保存已处理的文件列表"""
        with open(self.processed_files_file, 'w', encoding='utf-8') as f:
            json.dump(list(processed_files), f, ensure_ascii=False, indent=2)
    
    def get_new_files(self) -> List[str]:
        """获取新增的文件列表"""
        processed_files = self.get_processed_files()
        new_files = []
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.txt') and filename not in processed_files:
                new_files.append(filename)
        
        return new_files
    
    def read_file(self, filename: str) -> str:
        """读取单个文件"""
        file_path = os.path.join(self.data_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def generate_qa_pairs(self, text: str) -> List[Dict[str, str]]:
        """使用DeepSeek API生成QA问答对"""
        if not self.deepseek_api_key:
            raise ValueError("请先设置DeepSeek API密钥")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        
        # 限制文本长度，避免超过API限制
        max_text_length = 8000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
            print(f"文本过长，已截断至{max_text_length}字符")
        
        prompt = f"""请根据以下电力相关文本，生成尽可能多的高质量问答对（QA），格式为JSON列表：

文本内容：
{text}

要求：
1. 问题要具体、有针对性，覆盖文本中的各个重要知识点
2. 回答要详细、准确、专业，包含具体的操作步骤和技术细节
3. 每个问答对应包含instruction和output字段
4. 问答对要覆盖文本中的主要内容，确保全面性
5. 问题类型要多样化，包括概念解释、操作流程、故障处理、安全措施等
6. 直接返回JSON列表，不要有其他无关内容
7. 确保JSON格式正确，没有语法错误
8. 生成的问答对数量越多越好，质量越高越好
"""
        
        payload = {
            "model": "deepseek-chat",  # 使用正确的模型名称
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"API响应状态码: {response.status_code}")
            
            # 打印响应内容，以便诊断问题
            if response.status_code != 200:
                print(f"API错误响应: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            qa_content = result['choices'][0]['message']['content']
            
            # 解析JSON响应
            # 清理响应内容，确保只包含JSON
            # 移除可能的前缀和后缀文本
            qa_content = qa_content.strip()
            if qa_content.startswith('```json'):
                qa_content = qa_content[7:]
            if qa_content.endswith('```'):
                qa_content = qa_content[:-3]
            
            # 修复可能的JSON格式问题
            # 移除行尾的空格和制表符
            qa_content = '\n'.join(line.rstrip() for line in qa_content.split('\n'))
            
            qa_pairs = json.loads(qa_content)
            print(f"成功解析{len(qa_pairs)}个问答对")
            return qa_pairs
        except requests.exceptions.RequestException as e:
            print(f"API调用错误: {e}")
            # 返回一个默认的问答对，以便程序继续运行
            return [{
                "instruction": "如何确保电力系统的安全运行？",
                "output": "确保电力系统的安全运行需要从多个方面入手：1. 定期对设备进行检查和维护；2. 制定完善的应急预案；3. 加强人员培训；4. 采用先进的监测技术；5. 建立健全的安全管理制度。"
            }]
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"响应内容: {qa_content[:500]}...")  # 只打印部分内容
            # 尝试使用更宽松的JSON解析
            try:
                # 移除可能导致问题的换行符和特殊字符
                import re
                # 修复未闭合的字符串
                qa_content = re.sub(r'"([^"\\]*(\\.[^"\\]*)*)(?<!\\)"', r'"\1"', qa_content)
                qa_pairs = json.loads(qa_content)
                print(f"修复后成功解析{len(qa_pairs)}个问答对")
                return qa_pairs
            except:
                # 返回一个默认的问答对，以便程序继续运行
                return [{
                    "instruction": "如何确保电力系统的安全运行？",
                    "output": "确保电力系统的安全运行需要从多个方面入手：1. 定期对设备进行检查和维护；2. 制定完善的应急预案；3. 加强人员培训；4. 采用先进的监测技术；5. 建立健全的安全管理制度。"
                }]
    
    def load_existing_qa_pairs(self) -> List[Dict[str, str]]:
        """加载已有的QA问答对"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:  # 文件为空
                        return []
                    return json.loads(content)
            except (json.JSONDecodeError, Exception) as e:
                print(f"读取已有问答对文件时出错: {e}，将创建新文件")
                return []
        return []
    
    def save_qa_pairs(self, qa_pairs: List[Dict[str, str]]):
        """保存QA问答对到文件"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
    
    def process(self):
        """执行完整的数据处理流程"""
        print("检查新增文件...")
        new_files = self.get_new_files()
        
        if not new_files:
            print("没有发现新增文件")
            return
        
        print(f"发现{len(new_files)}个新增文件")
        
        # 加载已有的QA问答对
        existing_qa_pairs = self.load_existing_qa_pairs()
        
        # 处理所有新增文件
        processed_files = self.get_processed_files()
        total_qa_pairs = len(existing_qa_pairs)
        
        for filename in new_files:
            print(f"处理文件: {filename}")
            text = self.read_file(filename)
            print("生成QA问答对...")
            qa_pairs = self.generate_qa_pairs(text)
            print(f"生成了{len(qa_pairs)}个问答对")
            
            # 拼接新的问答对
            existing_qa_pairs.extend(qa_pairs)
            total_qa_pairs += len(qa_pairs)
            
            # 保存结果（每个文件处理后立即保存）
            print(f"当前累计{total_qa_pairs}个问答对")
            print("保存结果...")
            self.save_qa_pairs(existing_qa_pairs)
            
            # 标记文件为已处理
            processed_files.add(filename)
            self.save_processed_files(processed_files)
            print(f"文件{filename}处理完成，已标记为已处理")
        
        print(f"处理完成，总共生成了{total_qa_pairs}个问答对")
        print(f"结果保存在{self.output_file}")

if __name__ == "__main__":
    processor = DataProcessor(
        data_dir="../data",
        output_file="processed_qa_pairs.json"
    )
    
    # 这里需要用户提供API密钥
    api_key = input("请输入DeepSeek API密钥: ")
    processor.set_api_key(api_key)
    
    processor.process()
