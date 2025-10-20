#!/usr/bin/env python3
"""
Simple test for MiniMax API connectivity
"""

import asyncio
import aiohttp
import json
import sys

async def test_minimax_connection():
    """Test basic MiniMax API connection"""

    # Test connection to MiniMax API
    url = "https://api.minimaxi.com/v1/text/chatcompletion_v2"

    # Simple test payload
    payload = {
        "model": "abab6.5s-chat",
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ],
        "stream": False
    }

    headers = {
        "Authorization": "Bearer test-key",  # Will fail but should connect
        "Content-Type": "application/json"
    }

    try:
        print("Testing MiniMax API connection...")
        timeout = aiohttp.ClientTimeout(total=10, connect=5)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            print(f"Making request to {url}")
            async with session.post(url, headers=headers, json=payload) as response:
                print(f"Response status: {response.status}")
                response_text = await response.text()
                print(f"Response: {response_text[:200]}...")

                if response.status in [200, 401, 403]:
                    print("✅ Connection successful (API reachable)")
                    return True
                else:
                    print(f"❌ Unexpected status: {response.status}")
                    return False

    except aiohttp.ClientConnectorError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except asyncio.TimeoutError:
        print("❌ Connection timeout")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_network_connectivity():
    """Test general network connectivity"""
    test_urls = [
        "https://www.google.com",
        "https://api.openai.com",
        "https://httpbin.org/get"
    ]

    timeout = aiohttp.ClientTimeout(total=5, connect=3)

    for url in test_urls:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    print(f"✅ {url}: {response.status}")
        except Exception as e:
            print(f"❌ {url}: {e}")

if __name__ == "__main__":
    print("=== Network Connectivity Test ===")
    asyncio.run(test_network_connectivity())

    print("\n=== MiniMax API Test ===")
    success = asyncio.run(test_minimax_connection())

    if success:
        print("\n✅ MiniMax API is reachable")
    else:
        print("\n❌ MiniMax API connection failed")
        print("This could be due to:")
        print("  - Network connectivity issues")
        print("  - Firewall blocking the request")
        print("  - MiniMax API server issues")
        print("  - DNS resolution problems")