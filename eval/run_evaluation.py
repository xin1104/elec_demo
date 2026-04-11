#!/usr/bin/env python3
"""
电力运检模型评估主脚本
"""
import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))

def main():
    """主函数"""
    print("电力运检模型评估工具")
    print("=" * 50)
    print("1. 生成电力运检领域专业问题")
    print("2. 获取模型回答")
    print("3. 评估模型回答")
    print("4. 运行完整评估流程")
    print("0. 退出")
    print("=" * 50)
    
    choice = input("请输入选项: ")
    
    if choice == "1":
        print("\n生成电力运检领域专业问题...")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'generate_questions.py')}")
    elif choice == "2":
        print("\n获取模型回答...")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'get_model_answers.py')}")
    elif choice == "3":
        print("\n评估模型回答...")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'evaluate_answers.py')}")
    elif choice == "4":
        print("\n运行完整评估流程...")
        print("1. 生成电力运检领域专业问题")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'generate_questions.py')}")
        print("\n2. 获取模型回答")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'get_model_answers.py')}")
        print("\n3. 评估模型回答")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'evaluate_answers.py')}")
    elif choice == "0":
        print("退出程序")
        sys.exit()
    else:
        print("无效选项，请重新运行。")

if __name__ == "__main__":
    main()
