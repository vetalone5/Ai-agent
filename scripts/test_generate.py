"""Test article generation via OpenRouter."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.claude_client import ClaudeClient

async def main():
    client = ClaudeClient()
    print(f"Provider: {client.provider}")
    print(f"Model: {client.model}")
    print(f"Budget remaining: {client.tokens_remaining_today}")
    print()

    print("Generating test content...")
    try:
        result = await client.complete(
            system_prompt="Ты — SEO-копирайтер. Пиши на русском.",
            user_prompt="Напиши 3 заголовка для статьи на тему 'аналитика упоминаний бренда в нейросетях'. Формат: нумерованный список.",
            max_tokens=300,
            temperature=0.7,
        )
        print("Result:")
        print(result)
        print(f"\nTokens used: {client.tokens_used_today}")
        print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
