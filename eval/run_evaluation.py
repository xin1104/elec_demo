#!/usr/bin/env python3
"""
电力运检模型评估主脚本
"""
import os
import sys

sys.path.append(os.path.dirname(__file__))

def get_api_key():
    """获取API密钥，如果配置中的密钥无效则提示用户输入"""
    from config import DEEPSEEK_API_KEY
    if DEEPSEEK_API_KEY == "your_deepseek_api_key" or not DEEPSEEK_API_KEY:
        print("请输入DeepSeek API密钥: ", end="")
        api_key = input().strip()
        if not api_key:
            print("错误: API密钥不能为空")
            sys.exit(1)
        return api_key
    return DEEPSEEK_API_KEY

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
        api_key = get_api_key()
        from generate_questions import generate_questions
        generate_questions(api_key)
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
        api_key = get_api_key()

        print("\n1. 生成电力运检领域专业问题")
        from generate_questions import generate_questions
        generate_questions(api_key)

        print("\n2. 获取模型回答")
        from get_model_answers import main as get_answers_main
        get_answers_main()

        print("\n3. 评估模型回答")
        from evaluate_answers import auto_evaluate
        auto_evaluate(api_key)
    elif choice == "0":
        print("退出程序")
        sys.exit()
    else:
        print("无效选项，请重新运行。")

if __name__ == "__main__":
    main()
