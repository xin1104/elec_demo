import time
from typing import Any

import requests


def call_chat_completion(
    api_config,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
    purpose: str,
    retries: int = 3,
    timeout: int = 60,
    allow_reasoning_fallback: bool = False,
) -> str | None:
    """Call an OpenAI-compatible chat API with retry and return message content."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_config.api_key}",
    }
    payload: dict[str, Any] = {
        "model": api_config.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(api_config.api_url, headers=headers, json=payload, timeout=timeout)
            if response.status_code >= 400:
                print(f"{purpose} failed, attempt {attempt}/{retries}, HTTP {response.status_code}: {response.text[:500]}")
                response.raise_for_status()

            response_json = response.json()
            message = response_json.get("choices", [{}])[0].get("message", {})
            content = message.get("content")
            if content and content.strip():
                return content.strip()

            reasoning_content = message.get("reasoning_content")
            if allow_reasoning_fallback and reasoning_content and reasoning_content.strip():
                print(f"{purpose} returned empty content; using reasoning_content as fallback.")
                return reasoning_content.strip()

            print(f"{purpose} failed, attempt {attempt}/{retries}, empty API content: {str(response_json)[:1000]}")
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            print(f"{purpose} failed, attempt {attempt}/{retries}: {exc}")

        if attempt < retries:
            time.sleep(2 ** (attempt - 1))

    return None
