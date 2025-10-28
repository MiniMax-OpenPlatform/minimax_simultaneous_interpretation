"""
Whisper service for automatic speech recognition (ASR).
Uses Whisper Large model for high-accuracy transcription.
"""

import whisper
import logging
import torch
import numpy as np
from typing import Optional
import threading
import asyncio
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for Whisper Large model ASR"""

    def __init__(self, preload: bool = False):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._lock = threading.Lock()

        # Set persistent model directory
        self.model_dir = Path(__file__).parent.parent.parent / "models" / "whisper"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Set environment variable for Whisper to use our persistent directory
        os.environ['WHISPER_CACHE_DIR'] = str(self.model_dir)

        if preload:
            self.preload_model()

    def load_model(self):
        """Load Whisper Large model"""
        try:
            with self._lock:
                if self.model is None:
                    logger.info(f"Loading Whisper Large model from {self.model_dir}...")

                    # Check if model exists in persistent directory
                    model_path = self.model_dir / "large-v3.pt"
                    if model_path.exists():
                        logger.info(f"Loading model from persistent path: {model_path}")
                        self.model = whisper.load_model(str(model_path), device=self.device)
                    else:
                        logger.info(f"Model not found in persistent directory, downloading...")
                        # Load model with explicit download_root (will download if needed)
                        self.model = whisper.load_model("large", device=self.device, download_root=str(self.model_dir))

                    logger.info(f"Whisper Large model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise

    def _transcribe_sync(self, audio_data: np.ndarray, source_language: Optional[str] = None) -> dict:
        """
        Synchronous transcription function for thread execution

        Args:
            audio_data: Audio data as numpy array
            source_language: Source language code (e.g., 'zh', 'en') or None for auto-detection

        Returns:
            Transcription result dictionary
        """
        if self.model is None:
            raise RuntimeError("Whisper model not loaded")

        try:
            # Determine language parameter: use source_language if specified and not 'auto', otherwise auto-detect
            language_param = source_language if source_language and source_language != 'auto' else None

            # Log language selection for debugging
            if language_param:
                logger.info(f"Using specified source language: {language_param}")
            else:
                logger.info("Using automatic language detection")

            # Transcribe with Whisper Large (optimized for speed)
            result = self.model.transcribe(
                audio_data,
                language=language_param,  # Use specified language or auto-detect
                task="transcribe",
                verbose=False,
                temperature=0.0,
                best_of=1,
                beam_size=1,  # Reduced from 5 to 1 for faster processing
                patience=1.0,
                length_penalty=1.0,
                suppress_tokens="-1",
                initial_prompt=None,
                condition_on_previous_text=False,  # Disabled for better speed
                fp16=torch.cuda.is_available(),
                no_speech_threshold=0.6,  # Add threshold to skip silent segments
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0
            )

            return result

        except Exception as e:
            logger.error(f"Whisper transcription error: {str(e)}")
            raise

    async def transcribe_audio(self, audio_data: np.ndarray, source_language: Optional[str] = None) -> Optional[dict]:
        """
        Asynchronous transcription using Whisper Large

        Args:
            audio_data: Audio data as numpy array (sample_rate=16000)
            source_language: Source language code (e.g., 'zh', 'en') or None for auto-detection

        Returns:
            Transcription result with text and detected language, or None if failed
        """
        if self.model is None:
            self.load_model()

        try:
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._transcribe_sync,
                audio_data,
                source_language
            )

            # Extract transcription
            text = result["text"].strip()

            transcription = {
                "text": text,
                "language": result["language"],
                "segments": result.get("segments", []),
                "confidence": self._calculate_confidence(result)
            }

            logger.info(f"Transcription completed: '{transcription['text'][:100]}...' (Language: {transcription['language']})")
            return transcription

        except Exception as e:
            logger.error(f"Async transcription failed: {str(e)}")
            return None

    def _calculate_confidence(self, result: dict) -> float:
        """
        Calculate average confidence from segments

        Args:
            result: Whisper transcription result

        Returns:
            Average confidence score
        """
        segments = result.get("segments", [])
        if not segments:
            return 0.0

        total_confidence = 0.0
        total_duration = 0.0

        for segment in segments:
            # Use no_speech_prob as confidence indicator (inverted)
            confidence = 1.0 - segment.get("no_speech_prob", 0.5)
            duration = segment.get("end", 0) - segment.get("start", 0)

            total_confidence += confidence * duration
            total_duration += duration

        return total_confidence / total_duration if total_duration > 0 else 0.0

    def is_speech_detected(self, result: dict, threshold: float = 0.5) -> bool:
        """
        Check if speech was detected in the audio

        Args:
            result: Whisper transcription result
            threshold: Minimum confidence threshold

        Returns:
            True if speech detected with sufficient confidence
        """
        if not result or not result.get("text", "").strip():
            return False

        confidence = self._calculate_confidence(result)
        return confidence >= threshold

    def preload_model(self):
        """Preload model in background thread"""
        def load():
            try:
                self.load_model()
                logger.info("Whisper model preloaded successfully")
            except Exception as e:
                logger.error(f"Model preload failed: {str(e)}")

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_loaded": self.model is not None,
            "device": self.device,
            "model_name": "large",
            "cuda_available": torch.cuda.is_available(),
            "model_dir": str(self.model_dir),
            "cache_dir_exists": self.model_dir.exists()
        }


# Global instance with preloading enabled
whisper_service = WhisperService(preload=True)


def get_whisper_service() -> WhisperService:
    """Get the global Whisper service instance"""
    return whisper_service


async def test_whisper_service():
    """Test function for Whisper service"""
    import numpy as np

    service = get_whisper_service()

    # Create dummy audio data (1 second of silence at 16kHz)
    dummy_audio = np.zeros(16000, dtype=np.float32)

    try:
        logger.info("Testing Whisper service...")
        result = await service.transcribe_audio(dummy_audio)

        if result:
            print(f"Test result: {result}")
            print(f"Model info: {service.get_model_info()}")
        else:
            print("Test failed - no result returned")

    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_whisper_service())