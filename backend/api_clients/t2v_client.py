"""
T2V (Text-to-Voice) API client for speech synthesis.
Based on t2v.txt API documentation using WebSocket.
"""

import websockets
import json
import base64
import logging
import asyncio
import time
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class T2VClient:
    """Client for T2V speech synthesis API using WebSocket"""

    def __init__(self, api_key: str, voice_id: str = "male-qn-qingse"):
        self.api_key = api_key
        self.voice_id = voice_id
        self.ws_url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
        self.websocket = None
        self.session_id = None

    async def connect(self):
        """Establish WebSocket connection"""
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            # Try with extra_headers first, fallback to additional_headers if not supported
            try:
                self.websocket = await websockets.connect(self.ws_url, extra_headers=headers)
            except TypeError:
                # Fallback for older websockets library versions
                self.websocket = await websockets.connect(self.ws_url, additional_headers=headers)

            # Wait for connection success response
            response = await self.websocket.recv()
            response_data = json.loads(response)

            if response_data.get("event") == "connected_success":
                self.session_id = response_data.get("session_id")
                logger.info(f"T2V WebSocket connected successfully. Session ID: {self.session_id}")
                return True
            else:
                logger.error(f"T2V connection failed: {response_data}")
                return False

        except Exception as e:
            logger.error(f"T2V WebSocket connection error: {str(e)}")
            return False

    async def start_task(self):
        """Send task_start event to begin synthesis"""
        if not self.websocket:
            raise Exception("WebSocket not connected")

        task_start_msg = {
            "event": "task_start",
            "model": "speech-01-turbo",
            "language_boost": "Chinese",
            "voice_setting": {
                "voice_id": self.voice_id,
                "speed": 1,
                "vol": 1,
                "pitch": 0
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1
            }
        }

        try:
            await self.websocket.send(json.dumps(task_start_msg))

            # Wait for task_started response
            response = await self.websocket.recv()
            response_data = json.loads(response)

            if response_data.get("event") == "task_started":
                logger.info("T2V task started successfully")
                return True
            else:
                logger.error(f"T2V task start failed: {response_data}")
                return False

        except Exception as e:
            logger.error(f"T2V task start error: {str(e)}")
            return False

    async def synthesize_text(self, text: str, chunk_callback=None) -> Optional[dict]:
        """
        Synthesize text to speech with streaming support

        Args:
            text: Text to synthesize
            chunk_callback: Optional callback function for streaming chunks (chunk_data, is_final, format)

        Returns:
            Dict with complete audio data and format, or None if failed
        """
        if not self.websocket:
            raise Exception("WebSocket not connected")

        try:
            # Send task_continue event with text
            task_continue_msg = {
                "event": "task_continue",
                "text": text
            }

            await self.websocket.send(json.dumps(task_continue_msg))

            # Send task_finish event to signal end of input
            task_finish_msg = {
                "event": "task_finish"
            }

            await self.websocket.send(json.dumps(task_finish_msg))

            # Collect streaming audio chunks
            audio_chunks = []
            audio_format = "mp3"  # default
            total_chunks = 0
            last_chunk_info = None  # Store info for the last chunk

            last_chunk_time = time.time()
            chunk_timeout = 2.0  # 2 seconds timeout between chunks

            while True:
                try:
                    # Wait for next message with timeout
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=chunk_timeout)
                    response_data = json.loads(response)
                    last_chunk_time = time.time()

                    logger.warning(f"T2V streaming response: {response_data}")

                    if "data" in response_data and "audio" in response_data["data"]:
                        # Decode hex audio data (T2V returns hex-encoded audio)
                        audio_hex = response_data["data"]["audio"]
                        try:
                            audio_bytes = bytes.fromhex(audio_hex)
                        except ValueError:
                            # Fallback to base64 if hex fails
                            audio_bytes = base64.b64decode(audio_hex)

                        audio_chunks.append(audio_bytes)
                        total_chunks += 1

                        # Extract audio format from extra_info (usually in first chunk)
                        if "extra_info" in response_data and "audio_format" in response_data["extra_info"]:
                            audio_format = response_data["extra_info"]["audio_format"]

                        logger.info(f"T2V chunk {total_chunks}: {len(audio_bytes)} bytes")

                        # Store the chunk info for potential final marking (only if non-empty)
                        if len(audio_bytes) > 0:
                            last_chunk_info = (audio_bytes, audio_format)

                        # Call streaming callback if provided (not final yet)
                        if chunk_callback:
                            try:
                                if asyncio.iscoroutinefunction(chunk_callback):
                                    await chunk_callback(audio_bytes, False, audio_format)
                                else:
                                    chunk_callback(audio_bytes, False, audio_format)
                            except Exception as e:
                                logger.error(f"T2V chunk callback error: {str(e)}")

                    # Check for task completion
                    if response_data.get("event") == "task_finished":
                        logger.info(f"T2V streaming completed. Total chunks: {total_chunks}")
                        # Send a final completion signal - we need to mark the last chunk as final
                        if chunk_callback and total_chunks > 0 and last_chunk_info is not None:
                            try:
                                last_audio, last_format = last_chunk_info
                                logger.info(f"Sending final completion signal for task with {len(last_audio)} bytes in last chunk")
                                # Send the last chunk again but marked as final
                                if asyncio.iscoroutinefunction(chunk_callback):
                                    await chunk_callback(last_audio, True, last_format)
                                else:
                                    chunk_callback(last_audio, True, last_format)
                            except Exception as e:
                                logger.error(f"T2V final chunk callback error: {str(e)}")
                        elif chunk_callback:
                            # If no chunks were received, send an empty final chunk
                            try:
                                logger.info("Sending empty final chunk (no audio received)")
                                if asyncio.iscoroutinefunction(chunk_callback):
                                    await chunk_callback(b'', True, audio_format)
                                else:
                                    chunk_callback(b'', True, audio_format)
                            except Exception as e:
                                logger.error(f"T2V final empty chunk callback error: {str(e)}")
                        break

                    # Check for task failure
                    if response_data.get("event") == "task_failed":
                        logger.error(f"T2V synthesis failed: {response_data}")
                        return None

                except asyncio.TimeoutError:
                    # No more chunks received, assume stream is complete
                    logger.info(f"T2V streaming timeout - assuming complete. Total chunks: {total_chunks}")
                    # Send final callback if we have chunks
                    if chunk_callback and total_chunks > 0:
                        try:
                            # Get the last chunk to mark as final
                            last_audio = audio_chunks[-1] if audio_chunks else b''
                            if asyncio.iscoroutinefunction(chunk_callback):
                                await chunk_callback(last_audio, True, audio_format)
                            else:
                                chunk_callback(last_audio, True, audio_format)
                        except Exception as e:
                            logger.error(f"T2V final chunk callback error: {str(e)}")
                    break
                except Exception as e:
                    logger.error(f"T2V WebSocket error: {str(e)}")
                    break

            # Return combined audio data
            if audio_chunks:
                combined_audio = b''.join(audio_chunks)
                logger.info(f"T2V synthesis completed. Total audio size: {len(combined_audio)} bytes ({total_chunks} chunks), Format: {audio_format}")
                return {"audio_data": combined_audio, "format": audio_format}
            else:
                logger.error("No audio chunks received")
                return None

        except Exception as e:
            logger.error(f"T2V synthesis error: {str(e)}")
            return None

    async def finish_task(self):
        """Send task_finish event to end synthesis"""
        if not self.websocket:
            return

        try:
            task_finish_msg = {"event": "task_finish"}
            await self.websocket.send(json.dumps(task_finish_msg))

            # Wait for task_finished response
            response = await self.websocket.recv()
            response_data = json.loads(response)

            if response_data.get("event") == "task_finished":
                logger.info("T2V task finished successfully")
            else:
                logger.warning(f"T2V task finish response: {response_data}")

        except Exception as e:
            logger.error(f"T2V task finish error: {str(e)}")

    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            try:
                await self.finish_task()
                await self.websocket.close()
                logger.info("T2V WebSocket connection closed")
            except Exception as e:
                logger.error(f"T2V close error: {str(e)}")
            finally:
                self.websocket = None
                self.session_id = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        await self.start_task()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


class T2VService:
    """High-level service for T2V operations"""

    def __init__(self, api_key: str, voice_id: str = "male-qn-qingse"):
        self.api_key = api_key
        self.voice_id = voice_id

    async def text_to_speech(self, text: str, chunk_callback=None) -> Optional[dict]:
        """
        Convert text to speech using T2V API with streaming support

        Args:
            text: Text to convert
            chunk_callback: Optional callback for streaming chunks (chunk_data, is_final, format)

        Returns:
            Dict with audio data and format, or None if failed
            {"audio_data": bytes, "format": str}
        """
        try:
            async with T2VClient(self.api_key, self.voice_id) as client:
                return await client.synthesize_text(text, chunk_callback)
        except Exception as e:
            logger.error(f"T2V service error: {str(e)}")
            return None


async def test_t2v_client():
    """Test function for T2V client"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("T2V_API_KEY")
    voice_id = os.getenv("VOICE_ID", "male-qn-qingse")

    if not api_key:
        print("T2V_API_KEY not found in environment")
        return

    service = T2VService(api_key, voice_id)

    try:
        audio_data = await service.text_to_speech("Hello, this is a test message.")
        if audio_data:
            print(f"T2V test successful! Audio size: {len(audio_data)} bytes")
            # Optionally save audio file for testing
            with open("test_audio.mp3", "wb") as f:
                f.write(audio_data)
            print("Test audio saved as test_audio.mp3")
        else:
            print("T2V test failed - no audio data returned")
    except Exception as e:
        print(f"T2V test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_t2v_client())