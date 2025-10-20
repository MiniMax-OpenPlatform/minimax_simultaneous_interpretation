#!/usr/bin/env python3
"""
Direct test using translate.txt format with provided API key
"""

import requests
import asyncio
import aiohttp
import json

# API key provided by user
API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiIvIiwiVXNlck5hbWUiOiLlhq_pm68iLCJBY2NvdW50IjoiIiwiU3ViamVjdElEIjoiMTY4NjgzMzY3NzA0Njc4MCIsIlBob25lIjoiMTg4MTE0NDU3MjgiLCJHcm91cElEIjoiMTY4NjgzMzY3NzM2NTQ1OSIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6IjE3ODk5ODExMTNAcXEuY29tIiwiQ3JlYXRlVGltZSI6IjIwMjUtMDItMjEgMTg6MjA6MTciLCJUb2tlblR5cGUiOjEsImlzcyI6Im1pbmltYXgifQ.fxmF-4CPd3efpqdJImkuwHC4c6Ig91PJ-HI0Hn_U1gL80mA5Ku_uLXP7xwflpp5DtCf8C1tj48Itdbi_bLoh9gQ0ZHnNpDe_vEQqXBwpVe9CKnqkNeeneVa3lKCRW2iCzAS4CoucTBBq9pDpLZKI7bsXVOq6ONxjaOa4LPkMv7EjLZVzyQcDlKuVKU8_fdiPiWEa0cztILtkTBqYeUJ1sZnh4j0ncuve17ky0-q4m-MyVahLJPJIektp_Rnd95xZYqS2fn0874BSfihMKlT2xaZUhJ_hpYcVw-fSEKzR7T5nOmUDTTKXYHlqn0sLzcetz4AtdJ8zGicVoALqnpVLtA"

def test_requests_sync():
    """Test using requests library (same as translate.txt)"""
    print("=== Testing with requests (sync) ===")

    url = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    payload = {
        "model": "abab6.5s-chat",
        "messages": [
            {
               "role": "system",
               "name": "MiniMax AI",
               "content": "You are a professional translator."
             },
            {
               "role": "user",
                "name": "用户",
                "content": "请将以下文本翻译成英文：你好，世界！"
             },
        ],
        "stream": True,
    }

    try:
        print(f"Making request to: {url}")
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            print("✅ Request successful! Streaming response:")
            result_text = ""
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode("utf-8")
                    print(chunk_str)
                    print("————————————————————")

                    # Parse the data
                    if chunk_str.startswith('data: '):
                        try:
                            data = json.loads(chunk_str[6:])
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    result_text += content

                                if data['choices'][0].get('finish_reason') == 'stop':
                                    break
                        except json.JSONDecodeError:
                            continue

            print(f"\n✅ Final result: {result_text}")
            return True
        else:
            print(f"❌ Request failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Request timeout")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_aiohttp_async():
    """Test using aiohttp (same as our current implementation)"""
    print("\n=== Testing with aiohttp (async) ===")

    url = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    payload = {
        "model": "abab6.5s-chat",
        "messages": [
            {
               "role": "system",
               "name": "MiniMax AI",
               "content": "You are a professional translator."
             },
            {
               "role": "user",
                "name": "用户",
                "content": "请将以下文本翻译成英文：你好，世界！"
             },
        ],
        "stream": True,
    }

    try:
        print(f"Making async request to: {url}")
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                print(f"Response status: {response.status}")

                if response.status == 200:
                    print("✅ Async request successful! Streaming response:")
                    result_text = ""
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            print(line_str)
                            print("————————————————————")

                            if line_str.startswith('data: '):
                                try:
                                    data = json.loads(line_str[6:])
                                    if 'choices' in data and len(data['choices']) > 0:
                                        delta = data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            result_text += content

                                        if data['choices'][0].get('finish_reason') == 'stop':
                                            break
                                except json.JSONDecodeError:
                                    continue

                    print(f"\n✅ Final async result: {result_text}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Async request failed with status: {response.status}")
                    print(f"Response: {error_text}")
                    return False

    except asyncio.TimeoutError:
        print("❌ Async request timeout")
        return False
    except aiohttp.ClientError as e:
        print(f"❌ Async connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Async error: {e}")
        return False

if __name__ == "__main__":
    print("Testing MiniMax API with provided API key...")
    print(f"API Key: {API_KEY[:50]}...")

    # Test with requests (same as translate.txt)
    sync_success = test_requests_sync()

    # Test with aiohttp (same as our implementation)
    async_success = asyncio.run(test_aiohttp_async())

    print(f"\n=== Results ===")
    print(f"Sync (requests): {'✅ Success' if sync_success else '❌ Failed'}")
    print(f"Async (aiohttp): {'✅ Success' if async_success else '❌ Failed'}")

    if sync_success or async_success:
        print("\n✅ API is working! The issue is likely with network connectivity in the main application.")
    else:
        print("\n❌ API test failed. This could be due to:")
        print("  - Network connectivity issues")
        print("  - Invalid API key")
        print("  - API server issues")