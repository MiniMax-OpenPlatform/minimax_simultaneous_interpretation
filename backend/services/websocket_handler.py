"""
WebSocket handler for real-time communication between frontend and backend.
Manages audio streaming, transcription, translation, and synthesis.
"""

import asyncio
import json
import logging
import base64
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
import numpy as np

from .whisper_service import get_whisper_service
from .audio_processor import StreamingAudioProcessor
from .translation_queue import TranslationQueue
from ..api_clients.minimax_client import MiniMaxClient
from ..api_clients.t2a_client import T2AService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_data: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_data[client_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "audio_processor": None,
            "translation_queue": None,
            "config": {}
        }
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if client_id in self.connection_data:
            # Clean up resources
            data = self.connection_data[client_id]
            if data.get("audio_processor"):
                data["audio_processor"].stop_processing()
            if data.get("translation_queue"):
                asyncio.create_task(data["translation_queue"].stop_workers())
            del self.connection_data[client_id]

        logger.info(f"Client {client_id} disconnected and resources cleaned up")

    async def send_message(self, client_id: str, message: dict):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {str(e)}")
                self.disconnect(client_id)

    async def send_binary(self, client_id: str, data: bytes):
        """Send binary data to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_bytes(data)
            except Exception as e:
                logger.error(f"Failed to send binary to {client_id}: {str(e)}")
                self.disconnect(client_id)

    def get_connection_data(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get connection data for client"""
        return self.connection_data.get(client_id)


# Global connection manager
manager = ConnectionManager()


class WebSocketHandler:
    """WebSocket message handler"""

    def __init__(self, client_id: str, websocket: WebSocket):
        self.client_id = client_id
        self.websocket = websocket
        self.whisper_service = get_whisper_service()

    async def handle_message(self, message: dict):
        """Handle incoming WebSocket message"""
        try:
            msg_type = message.get("type")
            data = message.get("data", {})

            logger.info(f"📨 Received WebSocket message from {self.client_id}: type='{msg_type}', data_keys={list(data.keys()) if data else 'None'}")

            if msg_type == "configure":
                logger.info(f"🔧 Processing configure message for {self.client_id}")
                await self._handle_configure(data)
            elif msg_type == "start_recording":
                await self._handle_start_recording()
            elif msg_type == "stop_recording":
                await self._handle_stop_recording()
            elif msg_type == "audio_data":
                await self._handle_audio_data(data)
            elif msg_type == "get_status":
                await self._handle_get_status()
            elif msg_type == "clear_all_tasks":
                await self._handle_clear_all_tasks()
            else:
                await self._send_error(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Message handling error for {self.client_id}: {str(e)}")
            await self._send_error(f"Message handling error: {str(e)}")

    async def _handle_configure(self, config: dict):
        """Handle configuration message"""
        required_keys = ["minimax_api_key", "t2a_api_key", "voice_id", "target_language"]

        for key in required_keys:
            if key not in config:
                await self._send_error(f"Missing required configuration: {key}")
                return

        try:
            # Initialize API clients (without validation to avoid delays)
            minimax_client = MiniMaxClient(config["minimax_api_key"])
            t2a_service = T2AService(config["t2a_api_key"], config["voice_id"])

            # Clear any existing configuration for this client
            conn_data = manager.get_connection_data(self.client_id)
            if conn_data:
                # Stop any existing translation queue
                if conn_data.get("translation_queue"):
                    await conn_data["translation_queue"].stop_workers()
                # Stop any existing audio processor
                if conn_data.get("audio_processor"):
                    conn_data["audio_processor"].stop_processing()

            # Initialize translation queue with fresh API clients
            translation_queue = TranslationQueue(minimax_client, t2a_service)

            # Set callbacks
            translation_queue.set_callbacks(
                translation_callback=self._on_translation_complete,
                audio_callback=self._on_audio_complete,
                audio_chunk_callback=self._on_audio_chunk,
                error_callback=self._on_translation_error
            )

            # Start queue workers
            await translation_queue.start_workers()

            # Initialize audio processor with source language support
            source_language = config.get("source_language", "auto")
            logger.info(f"📝 Received source_language configuration: '{source_language}'")
            # Pass None for auto-detection, otherwise pass the specified language
            whisper_language = None if source_language == "auto" else source_language
            logger.info(f"📝 Whisper will use language parameter: {whisper_language}")
            audio_processor = StreamingAudioProcessor(self.whisper_service, source_language=whisper_language)

            # Store in connection data (only store config keys needed, not the full config with API keys)
            if conn_data:
                conn_data.update({
                    "config": {
                        "source_language": config.get("source_language", "auto"),
                        "target_language": config["target_language"],
                        "voice_id": config["voice_id"],
                        "hot_words": config.get("hot_words", []),
                        "translation_style": config.get("translation_style", "default")
                    },
                    "translation_queue": translation_queue,
                    "audio_processor": audio_processor
                })

            await self._send_message({
                "type": "configured",
                "data": {"status": "ready"}
            })

            logger.info(f"Client {self.client_id} configured successfully with validated API keys")

        except Exception as e:
            await self._send_error(f"Configuration failed: {str(e)}")

    async def _handle_start_recording(self):
        """Handle start recording message"""
        conn_data = manager.get_connection_data(self.client_id)
        if not conn_data or not conn_data.get("audio_processor"):
            await self._send_error("Not configured")
            return

        try:
            audio_processor = conn_data["audio_processor"]

            # Start audio processing in background
            asyncio.create_task(
                audio_processor.start_processing(
                    transcription_callback=self._on_transcription_complete,
                    error_callback=self._on_transcription_error
                )
            )

            await self._send_message({
                "type": "recording_started",
                "data": {"status": "recording"}
            })

            logger.info(f"Client {self.client_id} started recording")

        except Exception as e:
            await self._send_error(f"Start recording failed: {str(e)}")

    async def _handle_stop_recording(self):
        """Handle stop recording message"""
        conn_data = manager.get_connection_data(self.client_id)
        if not conn_data:
            return

        try:
            # Stop audio processor
            if conn_data.get("audio_processor"):
                conn_data["audio_processor"].force_process_current()
                conn_data["audio_processor"].stop_processing()

            await self._send_message({
                "type": "recording_stopped",
                "data": {"status": "stopped"}
            })

            logger.info(f"Client {self.client_id} stopped recording")

        except Exception as e:
            await self._send_error(f"Stop recording failed: {str(e)}")

    async def _handle_audio_data(self, data: dict):
        """Handle incoming audio data"""
        conn_data = manager.get_connection_data(self.client_id)
        if not conn_data or not conn_data.get("audio_processor"):
            await self._send_error("Audio processor not ready")
            return

        try:
            # Decode base64 audio data
            audio_base64 = data.get("audio")
            if not audio_base64:
                await self._send_error("No audio data provided")
                return

            audio_bytes = base64.b64decode(audio_base64)
            logger.info(f"🎤 Received audio chunk: {len(audio_bytes)} bytes")  # 改为INFO级别便于调试

            # Add to audio processor
            audio_processor = conn_data["audio_processor"]
            audio_processor.add_audio_data(audio_bytes)

        except Exception as e:
            logger.error(f"Audio data processing error: {str(e)}")
            await self._send_error(f"Audio processing failed: {str(e)}")

    async def _handle_get_status(self):
        """Handle status request"""
        conn_data = manager.get_connection_data(self.client_id)
        if not conn_data:
            await self._send_error("Not connected")
            return

        status = {
            "connected": True,
            "configured": bool(conn_data.get("config")),
            "recording": False
        }

        # Add audio processor stats
        if conn_data.get("audio_processor"):
            status["audio_stats"] = conn_data["audio_processor"].get_stats()

        # Add queue stats
        if conn_data.get("translation_queue"):
            status["queue_stats"] = conn_data["translation_queue"].get_queue_stats()

        await self._send_message({
            "type": "status",
            "data": status
        })

    async def _on_transcription_complete(self, result: dict):
        """Async callback for transcription completion"""
        logger.info(f"🎤 Transcription completed for {self.client_id}: '{result['text'][:50]}...'")

        # Send transcription result
        await self._send_message({
            "type": "transcription",
            "data": {
                "text": result["text"],
                "language": result["language"],
                "confidence": result.get("confidence", 0.0)
            }
        })

        # Add to translation queue
        conn_data = manager.get_connection_data(self.client_id)
        if conn_data and conn_data.get("translation_queue") and conn_data.get("config"):
            target_language = conn_data["config"]["target_language"]
            hot_words = conn_data["config"].get("hot_words", [])
            translation_style = conn_data["config"].get("translation_style", "default")

            await conn_data["translation_queue"].add_task(
                result["text"],
                target_language,
                hot_words,
                translation_style
            )
        else:
            logger.warning(f"Translation queue setup failed - missing configuration")


    async def _on_transcription_error(self, error: str):
        """Async callback for transcription errors"""
        await self._send_message({
            "type": "transcription_error",
            "data": {"error": error}
        })

    async def _on_translation_complete(self, task_id: str, result: dict):
        """Async callback for translation completion"""
        logger.info(f"📝 Translation completed for task {task_id}")

        # Send translation result
        await self._send_message({
            "type": "translation",
            "data": {
                "task_id": task_id,
                "original_text": result["original_text"],
                "translated_text": result["translated_text"],
                "target_language": result["target_language"]
            }
        })


    async def _on_audio_chunk(self, task_id: str, chunk_data: bytes, is_final: bool, audio_format: str):
        """Async callback for streaming audio chunks"""
        logger.info(f"_on_audio_chunk called: task_id={task_id}, size={len(chunk_data)}, is_final={is_final}, format={audio_format}")

        # Check if chunk_data is valid
        if not chunk_data:
            logger.warning(f"_on_audio_chunk: chunk_data is empty! task_id={task_id}, is_final={is_final}")
            # Still send the message to indicate final chunk
            if is_final:
                await self._send_message({
                    "type": "audio_chunk",
                    "data": {
                        "task_id": task_id,
                        "audio": "",
                        "format": audio_format,
                        "size": 0,
                        "is_final": is_final
                    }
                })
            return

        # Encode audio chunk as base64 for transmission
        chunk_base64 = base64.b64encode(chunk_data).decode('utf-8')
        logger.info(f"_on_audio_chunk: encoded base64 length={len(chunk_base64)}, first 50 chars: {chunk_base64[:50]}...")

        message_data = {
            "type": "audio_chunk",
            "data": {
                "task_id": task_id,
                "audio": chunk_base64,
                "format": audio_format,
                "size": len(chunk_data),
                "is_final": is_final
            }
        }
        logger.info(f"_on_audio_chunk: sending message with audio data length={len(message_data['data']['audio'])}")

        await self._send_message(message_data)

        # Add a small delay to avoid overwhelming the WebSocket
        if not is_final:
            await asyncio.sleep(0.01)  # 10ms delay between chunks

        logger.info(f"Audio chunk sent to frontend: task_id={task_id}, is_final={is_final}")

    async def _on_audio_complete(self, task_id: str, audio_data: bytes, audio_format: str = "mp3"):
        """Async callback for audio synthesis completion"""
        # Encode audio as base64 for transmission
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        await self._send_message({
            "type": "audio",
            "data": {
                "task_id": task_id,
                "audio": audio_base64,
                "format": audio_format,
                "size": len(audio_data)
            }
        })

    async def _on_translation_error(self, task_id: str, error: str):
        """Async callback for translation errors"""
        await self._send_message({
            "type": "translation_error",
            "data": {
                "task_id": task_id,
                "error": error
            }
        })

    async def _send_message(self, message: dict):
        """Send message to client"""
        await manager.send_message(self.client_id, message)


    async def _handle_clear_all_tasks(self):
        """Handle clear all tasks message"""
        try:
            logger.info(f"🧹 Clearing all tasks for client {self.client_id}")

            conn_data = manager.get_connection_data(self.client_id)
            if not conn_data:
                await self._send_error("Not configured")
                return

            # Stop audio processor if exists
            audio_processor = conn_data.get("audio_processor")
            if audio_processor:
                logger.info(f"🔇 Stopping audio processor for {self.client_id}")
                # Clear any accumulated audio data
                audio_processor.reset()

            # Clear translation queue tasks
            translation_queue = conn_data.get("translation_queue")
            if translation_queue:
                logger.info(f"🗑️ Clearing translation queue for {self.client_id}")
                # Cancel pending translations
                await translation_queue.clear_pending_tasks()

            # Send confirmation to client
            await self._send_message({
                "type": "all_tasks_cleared",
                "data": {"message": "所有任务已清除"}
            })

            logger.info(f"✅ All tasks cleared for client {self.client_id}")

        except Exception as e:
            logger.error(f"Clear all tasks error for {self.client_id}: {e}")
            await self._send_error(f"Failed to clear tasks: {str(e)}")

    async def _send_error(self, error: str):
        """Send error message to client"""
        await self._send_message({
            "type": "error",
            "data": {"error": error}
        })


async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint handler"""
    await manager.connect(websocket, client_id)
    handler = WebSocketHandler(client_id, websocket)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle message
            await handler.handle_message(message)

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {str(e)}")
    finally:
        manager.disconnect(client_id)