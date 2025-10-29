"""
Translation queue manager for handling concurrent translation and synthesis requests.
Implements smart queuing with timeout and prioritization.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TranslationTask:
    """Represents a translation task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    target_language: str = ""
    hot_words: list = field(default_factory=list)
    translation_style: str = "default"
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timeout_seconds: float = 45.0


class TranslationQueue:
    """Smart translation queue with timeout and concurrency control"""

    def __init__(self,
                 minimax_client,
                 t2a_service,
                 max_concurrent: int = 3,
                 default_timeout: float = 45.0):  # Increased timeout to allow for MiniMax API
        """
        Initialize translation queue

        Args:
            minimax_client: MiniMax translation client
            t2a_service: T2V speech synthesis service
            max_concurrent: Maximum concurrent translations
            default_timeout: Default timeout in seconds
        """
        # Store API client references but validate on each use
        self.minimax_client = minimax_client
        self.t2a_service = t2a_service
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout

        # Track client creation time for cache invalidation
        self.client_created_at = time.time()

        # Queue management
        self.pending_queue = asyncio.Queue()
        self.active_tasks: Dict[str, TranslationTask] = {}
        self.completed_tasks: Dict[str, TranslationTask] = {}

        # Callbacks
        self.translation_callback: Optional[Callable[[str, dict], None]] = None
        self.audio_callback: Optional[Callable[[str, bytes, str], None]] = None
        self.audio_chunk_callback: Optional[Callable[[str, bytes, bool, str], None]] = None  # For streaming
        self.error_callback: Optional[Callable[[str, str], None]] = None

        # Worker management
        self.workers: list = []
        self.is_running = False

    def set_callbacks(self,
                     translation_callback: Optional[Callable[[str, dict], None]] = None,
                     audio_callback: Optional[Callable[[str, bytes, str], None]] = None,
                     audio_chunk_callback: Optional[Callable[[str, bytes, bool, str], None]] = None,
                     error_callback: Optional[Callable[[str, str], None]] = None):
        """Set result callbacks"""
        self.translation_callback = translation_callback
        self.audio_callback = audio_callback
        self.audio_chunk_callback = audio_chunk_callback
        self.error_callback = error_callback

    async def add_task(self, text: str, target_language: str, hot_words: list = None, translation_style: str = "default", timeout: Optional[float] = None) -> str:
        """
        Add translation task to queue

        Args:
            text: Text to translate
            target_language: Target language
            hot_words: List of hot words/professional terms
            translation_style: Translation style (default, colloquial, business, academic)
            timeout: Custom timeout for this task

        Returns:
            Task ID
        """
        task = TranslationTask(
            text=text,
            target_language=target_language,
            hot_words=hot_words or [],
            translation_style=translation_style,
            timeout_seconds=timeout or self.default_timeout
        )

        # Clean up old completed tasks
        await self._cleanup_old_tasks()

        # Check queue size
        if self.pending_queue.qsize() >= self.max_concurrent:
            logger.warning("Queue full, dropping oldest pending task")
            try:
                # Remove oldest pending task
                oldest_task = await asyncio.wait_for(self.pending_queue.get(), timeout=0.1)
                oldest_task.status = TaskStatus.FAILED
                oldest_task.error = "Queue overflow"
                logger.warning(f"Dropped task {oldest_task.id} due to queue overflow")
            except asyncio.TimeoutError:
                pass

        await self.pending_queue.put(task)
        logger.info(f"Added translation task {task.id}: '{text[:50]}...' -> {target_language}")
        return task.id

    async def _validate_api_clients(self) -> bool:
        """Validate that API clients are still functional"""
        try:
            # Test a simple translation to ensure API keys are valid
            test_result = await self.minimax_client.translate_text("test", "English")
            if not test_result or not test_result.strip():
                logger.error("MiniMax API client validation failed - empty result")
                return False

            # T2V client validation is more complex, will be tested during actual use
            logger.debug("API clients validation passed")
            return True
        except Exception as e:
            logger.error(f"API client validation failed: {str(e)}")
            return False

    async def start_workers(self):
        """Start worker tasks"""
        if self.is_running:
            return

        self.is_running = True

        # Start worker tasks
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        logger.info(f"Started {len(self.workers)} translation workers")

    async def stop_workers(self):
        """Stop all workers"""
        self.is_running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers = []
        logger.info("All translation workers stopped")

    async def _worker(self, worker_name: str):
        """Worker coroutine for processing translation tasks"""
        logger.info(f"Translation worker {worker_name} started")

        while self.is_running:
            try:
                # Get task from queue
                task = await asyncio.wait_for(self.pending_queue.get(), timeout=1.0)

                # Check if task is still valid
                if time.time() - task.created_at > task.timeout_seconds:
                    task.status = TaskStatus.TIMEOUT
                    task.error = "Task timeout before processing"
                    logger.warning(f"Task {task.id} timed out before processing")
                    continue

                # Process task
                await self._process_task(task, worker_name)

            except asyncio.TimeoutError:
                # No tasks available, continue polling
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {str(e)}")

        logger.info(f"Translation worker {worker_name} stopped")

    async def _process_task(self, task: TranslationTask, worker_name: str):
        """Process a single translation task"""
        task.status = TaskStatus.PROCESSING
        task.started_at = time.time()
        self.active_tasks[task.id] = task

        logger.info(f"Worker {worker_name} processing task {task.id}")
        task_start_time = asyncio.get_event_loop().time()

        try:
            # Step 1: Translate text
            translation_start_time = asyncio.get_event_loop().time()
            translated_text = await asyncio.wait_for(
                self.minimax_client.translate_text(task.text, task.target_language, task.hot_words, task.translation_style),
                timeout=35  # Fixed timeout of 35 seconds (longer than MiniMax client's 30s)
            )
            translation_end_time = asyncio.get_event_loop().time()
            translation_duration = (translation_end_time - translation_start_time) * 1000
            logger.info(f"⏱️ Translation Performance: {translation_duration:.0f}ms for '{task.text[:30]}...' -> '{translated_text[:30]}...'")

            if not translated_text or not translated_text.strip():
                raise Exception("Translation returned empty result")

            # Prepare translation result
            translation_result = {
                "original_text": task.text,
                "translated_text": translated_text,
                "target_language": task.target_language,
                "task_id": task.id
            }

            # Notify translation completion
            if self.translation_callback:
                if asyncio.iscoroutinefunction(self.translation_callback):
                    await self.translation_callback(task.id, translation_result)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.translation_callback, task.id, translation_result
                    )

            # Step 2: Text-to-speech synthesis
            # Define streaming chunk callback
            async def chunk_callback(chunk_data: bytes, is_final: bool, audio_format: str):
                if self.audio_chunk_callback:
                    if asyncio.iscoroutinefunction(self.audio_chunk_callback):
                        await self.audio_chunk_callback(task.id, chunk_data, is_final, audio_format)
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.audio_chunk_callback, task.id, chunk_data, is_final, audio_format
                        )

            tts_start_time = asyncio.get_event_loop().time()
            audio_data = await asyncio.wait_for(
                self.t2a_service.text_to_speech(translated_text, chunk_callback),
                timeout=task.timeout_seconds * 0.4  # 40% of timeout for synthesis
            )
            tts_end_time = asyncio.get_event_loop().time()
            tts_duration = (tts_end_time - tts_start_time) * 1000

            if audio_data:
                # Extract audio bytes and format for logging
                if isinstance(audio_data, dict):
                    audio_size = len(audio_data["audio_data"])
                else:
                    audio_size = len(audio_data)

                # NOTE: We don't send the complete audio anymore, only streaming chunks
                # This prevents duplicate audio playback (streaming + complete)
                logger.info(f"Audio synthesis completed for task {task.id}, size: {audio_size} bytes")

                task.result = {
                    **translation_result,
                    "audio_size": audio_size
                }
            else:
                task.result = translation_result
                logger.warning(f"Audio synthesis failed for task {task.id}")

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task_end_time = asyncio.get_event_loop().time()
            total_duration = (task_end_time - task_start_time) * 1000

            logger.info(f"⏱️ Translation Performance: {translation_duration:.0f}ms for '{task.text[:30]}...'")
            logger.info(f"⏱️ TTS Performance: {tts_duration:.0f}ms for {len(translated_text)} chars")
            logger.info(f"⏱️ Total Task Performance: {total_duration:.0f}ms (Translation: {translation_duration:.0f}ms, TTS: {tts_duration:.0f}ms)")
            logger.info(f"Task {task.id} completed successfully in {task.completed_at - task.started_at:.2f}s")

        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task timeout after {task.timeout_seconds}s"
            logger.warning(f"Task {task.id} timed out")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"Task {task.id} failed: {str(e)}")

            # Notify error
            if self.error_callback:
                if asyncio.iscoroutinefunction(self.error_callback):
                    await self.error_callback(task.id, str(e))
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.error_callback, task.id, str(e)
                    )

        finally:
            # Move to completed tasks
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            self.completed_tasks[task.id] = task

    async def _cleanup_old_tasks(self):
        """Clean up old completed tasks"""
        current_time = time.time()
        cleanup_age = 300  # 5 minutes

        to_remove = []
        for task_id, task in self.completed_tasks.items():
            if current_time - task.created_at > cleanup_age:
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.completed_tasks[task_id]

        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old tasks")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID"""
        # Check active tasks
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
        elif task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
        else:
            return None

        return {
            "id": task.id,
            "status": task.status.value,
            "text": task.text[:100] + "..." if len(task.text) > 100 else task.text,
            "target_language": task.target_language,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "duration": (task.completed_at - task.started_at) if task.started_at and task.completed_at else None,
            "error": task.error,
            "result": task.result
        }

    async def clear_pending_tasks(self):
        """Clear all pending tasks and cancel active tasks"""
        # Clear pending queue
        cleared_pending = 0
        while not self.pending_queue.empty():
            try:
                task = self.pending_queue.get_nowait()
                task.status = TaskStatus.FAILED
                task.error = "Task cleared by user"
                cleared_pending += 1
            except asyncio.QueueEmpty:
                break

        # Cancel active tasks
        cleared_active = 0
        for task_id, task in list(self.active_tasks.items()):
            task.status = TaskStatus.FAILED
            task.error = "Task cancelled by user"
            cleared_active += 1

        # Clear completed tasks
        cleared_completed = len(self.completed_tasks)
        self.completed_tasks.clear()

        logger.info(f"Translation queue cleared: {cleared_pending} pending, {cleared_active} active, {cleared_completed} completed")

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "pending_count": self.pending_queue.qsize(),
            "active_count": len(self.active_tasks),
            "completed_count": len(self.completed_tasks),
            "max_concurrent": self.max_concurrent,
            "is_running": self.is_running,
            "workers_count": len(self.workers)
        }


async def test_translation_queue():
    """Test function for translation queue"""
    from ..api_clients.minimax_client import MiniMaxClient
    from ..api_clients.t2v_client import T2VService
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize clients
    minimax_key = os.getenv("MINIMAX_API_KEY")
    t2v_key = os.getenv("T2V_API_KEY")
    voice_id = os.getenv("VOICE_ID", "male-qn-qingse")

    if not minimax_key or not t2v_key:
        print("API keys not found in environment")
        return

    minimax_client = MiniMaxClient(minimax_key)
    t2a_service = T2VService(t2v_key, voice_id)

    # Initialize queue
    queue = TranslationQueue(minimax_client, t2a_service)

    # Set callbacks
    def on_translation(task_id, result):
        print(f"Translation {task_id}: {result['translated_text']}")

    def on_audio(task_id, audio_data):
        print(f"Audio {task_id}: {len(audio_data)} bytes")

    def on_error(task_id, error):
        print(f"Error {task_id}: {error}")

    queue.set_callbacks(on_translation, on_audio, on_error)

    # Start workers
    await queue.start_workers()

    try:
        # Add test tasks
        task1 = await queue.add_task("你好，世界！", "English")
        task2 = await queue.add_task("今天天气不错", "English")

        # Wait for completion
        await asyncio.sleep(10)

        # Check stats
        print(f"Queue stats: {queue.get_queue_stats()}")
        print(f"Task1 status: {queue.get_task_status(task1)}")
        print(f"Task2 status: {queue.get_task_status(task2)}")

    finally:
        await queue.stop_workers()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_translation_queue())