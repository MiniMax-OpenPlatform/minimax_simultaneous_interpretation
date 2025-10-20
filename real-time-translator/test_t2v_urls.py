#!/usr/bin/env python3
"""
Test different T2V WebSocket URLs to find the correct one
"""

import asyncio
import websockets
import json

# API key from user
API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiIvIiwiVXNlck5hbWUiOiLlhq_pm68iLCJBY2NvdW50IjoiIiwiU3ViamVjdElEIjoiMTY4NjgzMzY3NzA0Njc4MCIsIlBob25lIjoiMTg4MTE0NDU3MjgiLCJHcm91cElEIjoiMTY4NjgzMzY3NzM2NTQ1OSIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6IjE3ODk5ODExMTNAcXEuY29tIiwiQ3JlYXRlVGltZSI6IjIwMjUtMDItMjEgMTg6MjA6MTciLCJUb2tlblR5cGUiOjEsImlzcyI6Im1pbmltYXgifQ.fxmF-4CPd3efpqdJImkuwHC4c6Ig91PJ-HI0Hn_U1gL80mA5Ku_uLXP7xwflpp5DtCf8C1tj48Itdbi_bLoh9gQ0ZHnNpDe_vEQqXBwpVe9CKnqkNeeneVa3lKCRW2iCzAS4CoucTBBq9pDpLZKI7bsXVOq6ONxjaOa4LPkMv7EjLZVzyQcDlKuVKU8_fdiPiWEa0cztILtkTBqYeUJ1sZnh4j0ncuve17ky0-q4m-MyVahLJPJIektp_Rnd95xZYqS2fn0874BSfihMKlT2xaZUhJ_hpYcVw-fSEKzR7T5nOmUDTTKXYHlqn0sLzcetz4AtdJ8zGicVoALqnpVLtA"

# Possible T2V WebSocket URLs
test_urls = [
    "wss://api.minimaxi.com/v1/t2a_ws",
    "wss://api.minimaxi.com/v1/text/speech_stream",
    "wss://api.minimaxi.com/v1/speech",
    "wss://api.minimaxi.com/v1/tts",
    "wss://api.minimaxi.com/v1/text_to_speech",
    "wss://api.minimaxi.com/ws/v1/text_to_speech",
    "wss://api.minimaxi.com/ws/v1/t2a",
    "wss://api.minimaxi.com/v1/audio/speech"
]

async def test_websocket_url(url):
    """Test a single WebSocket URL"""
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    try:
        print(f"\n🔍 Testing: {url}")

        # Try different header parameter names
        try:
            websocket = await websockets.connect(url, extra_headers=headers)
        except TypeError:
            websocket = await websockets.connect(url, additional_headers=headers)

        print(f"✅ Connection successful: {url}")

        # Try to receive welcome message
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            print(f"✅ Response received: {response_data}")

            if "session_id" in response_data:
                print(f"🎉 FOUND WORKING URL: {url}")
                await websocket.close()
                return url
        except asyncio.TimeoutError:
            print(f"⏰ Connection timeout - no response")
        except json.JSONDecodeError:
            print(f"📄 Non-JSON response received")

        await websocket.close()
        return None

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ HTTP Error {e.status_code}: {url}")
    except websockets.exceptions.ConnectionClosedError:
        print(f"❌ Connection closed immediately: {url}")
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

    return None

async def test_all_urls():
    """Test all possible T2V URLs"""
    print("🔍 Testing T2V WebSocket URLs...")

    working_urls = []

    for url in test_urls:
        result = await test_websocket_url(url)
        if result:
            working_urls.append(result)

    print(f"\n📊 Results:")
    if working_urls:
        print(f"✅ Working URLs found: {len(working_urls)}")
        for url in working_urls:
            print(f"  - {url}")
    else:
        print("❌ No working URLs found")
        print("Possible issues:")
        print("  - T2V API might not be available via WebSocket")
        print("  - API key might not have T2V access")
        print("  - Different authentication method required")
        print("  - Service might be temporarily down")

    return working_urls

if __name__ == "__main__":
    asyncio.run(test_all_urls())