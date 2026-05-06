#!/usr/bin/env python3
"""
电力运检模型评估主脚本
"""
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api_options import prompt_api_config


def get_api_config():
    """获取 API 配置，如果配置中的密钥无效则提示用户选择服务商和模型"""
    from config import DEEPSEEK_API_KEY
    try:
        return prompt_api_config(None if DEEPSEEK_API_KEY == "your_deepseek_api_key" else DEEPSEEK_API_KEY)
    except ValueError as exc:
        print(f"错误: {exc}")
        sys.exit(1)

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
        api_config = get_api_config()
        from generate_questions import generate_questions
        generate_questions(api_config)
    elif choice == "2":
        print("\n获取模型回答...")
        from get_model_answers import main as get_answers_main
        get_answers_main()
    elif choice == "3":
        print("\n评估模型回答...")
        from evaluate_answers import main as evaluate_main
        evaluate_main()
    elif choice == "4":
        print("\n运行完整评估流程...")
        api_config = get_api_config()

        print("\n1. 生成电力运检领域专业问题")
        from generate_questions import generate_questions
        generate_questions(api_config)

        print("\n2. 获取模型回答")
        from get_model_answers import main as get_answers_main
        get_answers_main()

        print("\n3. 评估模型回答")
        from evaluate_answers import auto_evaluate
        auto_evaluate(api_config)
    elif choice == "0":
        print("退出程序")
        sys.exit()
    else:
        print("无效选项，请重新运行。")

if __name__ == "__main__":
    main()
