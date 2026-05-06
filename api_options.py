from dataclasses import dataclass
from typing import Optional


@dataclass
class ApiConfig:
    provider: str
    model: str
    api_key: str
    api_url: str


PROVIDERS = [
    {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": [
            "deepseek-chat",
            "deepseek-reasoner",
        ],
    },
    {
        "name": "Xiaomi MiMo",
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "models": [
            "mimo-v2.5-pro",
            "mimo-v2.5",
            "mimo-v2-pro",
            "mimo-v2-omni",
        ],
    },
]


def chat_completions_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url}/chat/completions"


def choose_from_menu(title: str, options: list[str]) -> str:
    while True:
        print(title)
        for index, option in enumerate(options, 1):
            print(f"{index}. {option}")

        choice = input("请输入选项编号: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]

        print("无效选项，请重新输入。\n")


def prompt_api_config(default_api_key: Optional[str] = None) -> ApiConfig:
    provider_names = [provider["name"] for provider in PROVIDERS]
    provider_name = choose_from_menu("请选择 API 服务商:", provider_names)
    provider = next(item for item in PROVIDERS if item["name"] == provider_name)
    model = choose_from_menu(f"请选择 {provider_name} 模型:", provider["models"])

    api_key = default_api_key if provider_name == "DeepSeek" else ""
    if not api_key or api_key == "your_deepseek_api_key":
        api_key = input(f"请输入 {provider_name} API key: ").strip()

    if not api_key:
        raise ValueError("API key 不能为空")

    return ApiConfig(
        provider=provider_name,
        model=model,
        api_key=api_key,
        api_url=chat_completions_url(provider["base_url"]),
    )


def ensure_api_config(value: Optional[ApiConfig | str]) -> ApiConfig:
    if isinstance(value, ApiConfig):
        return value

    if isinstance(value, str) and value:
        return ApiConfig(
            provider="DeepSeek",
            model="deepseek-chat",
            api_key=value,
            api_url="https://api.deepseek.com/v1/chat/completions",
        )

    return prompt_api_config()
