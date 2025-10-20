"""
MiniMax API client for text translation.
Based on translate.txt API documentation.
"""

import requests
import json
import logging
from typing import AsyncGenerator, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MiniMaxClient:
    """Client for MiniMax translation API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.executor = ThreadPoolExecutor(max_workers=3)

    def _translate_sync(self, text: str, target_language: str, hot_words: list = None, translation_style: str = "default") -> str:
        """
        Synchronous translation method using requests (working implementation)
        """
        # 构建热词提示
        hot_words_prompt = ""
        if hot_words and len(hot_words) > 0:
            hot_words_str = "、".join(hot_words)
            hot_words_prompt = f"\n专业术语和热词包括：{hot_words_str}\n请特别注意这些术语的准确翻译。\n"

        # 构建翻译风格提示
        style_prompt = ""
        style_instructions = ""

        if translation_style == "colloquial":
            style_prompt = "\n翻译风格：口语化\n"
            style_instructions = "- Use colloquial and conversational language\n- Prefer informal expressions and everyday vocabulary\n- Make the translation sound natural in spoken language\n"
        elif translation_style == "business":
            style_prompt = "\n翻译风格：商务场景\n"
            style_instructions = "- Use formal and professional business language\n- Employ proper business terminology and etiquette\n- Maintain a professional and courteous tone\n"
        elif translation_style == "academic":
            style_prompt = "\n翻译风格：学术场景\n"
            style_instructions = "- Use formal academic language and terminology\n- Employ precise and scholarly expressions\n- Maintain objectivity and academic rigor\n"

        prompt = f"""You are a professional translator. Translate the following text from its original language to {target_language}.
{hot_words_prompt}{style_prompt}
IMPORTANT RULES:
- Output ONLY the translated text
- Do NOT include explanations, notes, or phrases like "The result of X is Y"
- Do NOT add quotation marks around the translation
- Do NOT mention the original text
- Do NOT add any prefixes or suffixes
- Keep the same tone and meaning
- Pay special attention to the professional terms and hot words mentioned above
{style_instructions}
Text to translate: {text}

Translation:"""

        payload = {
            "model": "abab6.5s-chat",
            "messages": [
                {
                    "role": "system",
                    "name": "MiniMax AI",
                    "content": "You are a professional translator. Translate the text accurately and naturally."
                },
                {
                    "role": "user",
                    "name": "用户",
                    "content": prompt
                }
            ],
            "stream": True,
        }

        logger.info(f"Starting translation request for text: '{text[:50]}...' to {target_language}")

        try:
            response = requests.post(
                self.url,
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=30  # 30 second timeout
            )

            logger.debug(f"Response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code}, response: {response.text}")
                raise Exception(f"API request failed: {response.status_code} - {response.text}")

            translated_text = ""
            logger.debug("Starting to read streaming response")

            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode("utf-8").strip()
                    if chunk_str.startswith('data: '):
                        try:
                            data = json.loads(chunk_str[6:])  # Remove "data: " prefix
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    translated_text += content
                                    logger.debug(f"Received content chunk: '{content}'")

                                # Check if translation is complete
                                if data['choices'][0].get('finish_reason') == 'stop':
                                    logger.info(f"Translation completed: '{translated_text[:50]}...'")
                                    break
                        except json.JSONDecodeError:
                            logger.debug(f"JSON decode error for line: {chunk_str[:100]}")
                            continue

            if not translated_text.strip():
                logger.warning("No translation content received")
                return text  # Return original text if translation failed

            return translated_text.strip()

        except requests.exceptions.Timeout:
            logger.error(f"Translation timeout for text: '{text[:50]}...'")
            raise Exception("Translation timeout")
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"Connection error during translation: {str(ce)}")
            raise Exception(f"Network error: {str(ce)}")
        except Exception as e:
            logger.error(f"Translation failed for text: '{text[:50]}...' - {str(e)}")
            raise Exception(f"Translation API error: {str(e)}")

    async def translate_text(self, text: str, target_language: str, hot_words: list = None, translation_style: str = "default") -> str:
        """
        Async wrapper for translation using ThreadPoolExecutor
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._translate_sync, text, target_language, hot_words, translation_style
        )


async def test_minimax_client():
    """Test function for MiniMax client"""
    import os

    # Get API key from environment variable
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("MINIMAX_API_KEY not found in environment variables")
        print("Please set MINIMAX_API_KEY environment variable")
        return

    client = MiniMaxClient(api_key)

    try:
        result = await client.translate_text("你好，世界！", "English")
        print(f"Translation result: {result}")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_minimax_client())