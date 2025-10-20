"""
Audio processor with Voice Activity Detection (VAD) for real-time audio processing.
Handles audio chunking, VAD, and integration with Whisper ASR.
"""

import webrtcvad
import numpy as np
import asyncio
import logging
from typing import List, Optional, Callable, AsyncGenerator
from collections import deque
import audioop
import io
import wave

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Audio processor with VAD for real-time speech detection"""

    def __init__(self,
                 sample_rate: int = 16000,
                 frame_duration_ms: int = 30,
                 vad_mode: int = 3,  # Strictest VAD mode to minimize false positives
                 silence_threshold_ms: int = 500,  # Faster speech segment detection
                 min_speech_duration_ms: int = 800):  # Much longer minimum to filter out short noise
        """
        Initialize audio processor

        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            frame_duration_ms: Frame duration in milliseconds (10, 20, or 30)
            vad_mode: VAD aggressiveness (0=least aggressive, 3=most aggressive)
            silence_threshold_ms: Silence duration to trigger processing
            min_speech_duration_ms: Minimum speech duration to process
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.vad_mode = vad_mode
        self.silence_threshold_ms = silence_threshold_ms
        self.min_speech_duration_ms = min_speech_duration_ms

        # Calculate frame size
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.frame_bytes = self.frame_size * 2  # 16-bit audio

        # Initialize VAD
        self.vad = webrtcvad.Vad(vad_mode)

        # Audio buffers
        self.audio_buffer = deque()
        self.speech_frames = []
        self.silence_frames = 0
        self.silence_threshold_frames = int(silence_threshold_ms / frame_duration_ms)
        self.min_speech_frames = int(min_speech_duration_ms / frame_duration_ms)

        # State tracking
        self.is_speaking = False
        self.speech_started = False

    def add_audio_chunk(self, audio_data: bytes) -> List[np.ndarray]:
        """
        Add audio chunk and return completed speech segments

        Args:
            audio_data: Raw audio data (16-bit PCM)

        Returns:
            List of completed speech segments as numpy arrays
        """
        # Add to buffer
        self.audio_buffer.extend(audio_data)
        completed_segments = []

        # Process frames
        while len(self.audio_buffer) >= self.frame_bytes:
            # Extract frame
            frame_data = bytes([self.audio_buffer.popleft() for _ in range(self.frame_bytes)])

            # Process frame
            segment = self._process_frame(frame_data)
            if segment is not None:
                completed_segments.append(segment)

        return completed_segments

    def _process_frame(self, frame_data: bytes) -> Optional[np.ndarray]:
        """
        Process a single audio frame

        Args:
            frame_data: Audio frame data

        Returns:
            Completed speech segment or None
        """
        try:
            # VAD detection
            is_speech = self.vad.is_speech(frame_data, self.sample_rate)

            if is_speech:
                # Speech detected
                self.speech_frames.append(frame_data)
                self.silence_frames = 0

                if not self.speech_started:
                    self.speech_started = True
                    logger.debug("Speech started")

            else:
                # Silence detected
                if self.speech_started:
                    self.silence_frames += 1

                    # Add some silence frames to the end for context
                    if self.silence_frames <= 3:  # Add up to 3 silence frames
                        self.speech_frames.append(frame_data)

                    # Check if silence threshold reached
                    if self.silence_frames >= self.silence_threshold_frames:
                        # End of speech segment
                        if len(self.speech_frames) >= self.min_speech_frames:
                            segment = self._finalize_segment()
                            self._reset_state()
                            return segment
                        else:
                            # Too short, discard
                            logger.debug(f"Discarding short segment: {len(self.speech_frames)} frames < {self.min_speech_frames} min")
                            self._reset_state()

        except Exception as e:
            logger.error(f"Frame processing error: {str(e)}")

        return None

    def _finalize_segment(self) -> np.ndarray:
        """
        Finalize and return speech segment

        Returns:
            Audio segment as numpy array
        """
        if not self.speech_frames:
            return np.array([])

        # Concatenate all speech frames
        audio_bytes = b''.join(self.speech_frames)

        # Convert to numpy array (16-bit PCM to float32)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        audio_array = audio_array / 32768.0  # Normalize to [-1, 1]

        logger.info(f"Finalized speech segment: {len(audio_array)/self.sample_rate:.2f}s")
        return audio_array

    def _reset_state(self):
        """Reset processing state"""
        self.speech_frames = []
        self.silence_frames = 0
        self.speech_started = False

    def force_segment(self) -> Optional[np.ndarray]:
        """
        Force completion of current segment

        Returns:
            Current segment or None if empty or too short
        """
        if len(self.speech_frames) >= self.min_speech_frames:
            segment = self._finalize_segment()
            self._reset_state()
            return segment
        elif self.speech_frames:
            logger.debug(f"Forcing discard of short segment: {len(self.speech_frames)} frames < {self.min_speech_frames} min")
            self._reset_state()
        return None

    def get_stats(self) -> dict:
        """Get processor statistics"""
        return {
            "sample_rate": self.sample_rate,
            "frame_duration_ms": self.frame_duration_ms,
            "vad_mode": self.vad_mode,
            "silence_threshold_ms": self.silence_threshold_ms,
            "buffer_size": len(self.audio_buffer),
            "speech_frames": len(self.speech_frames),
            "is_speaking": self.speech_started
        }


class StreamingAudioProcessor:
    """Streaming audio processor for real-time processing"""

    def __init__(self,
                 whisper_service,
                 sample_rate: int = 16000,
                 vad_mode: int = 3,  # Strictest VAD mode to minimize false positives
                 silence_threshold_ms: int = 500,  # Faster speech segment detection
                 min_speech_duration_ms: int = 800):  # Much longer minimum to filter out short noise
        """
        Initialize streaming processor

        Args:
            whisper_service: Whisper service instance
            sample_rate: Audio sample rate
            vad_mode: VAD aggressiveness
            silence_threshold_ms: Silence threshold
            min_speech_duration_ms: Minimum speech duration
        """
        self.whisper_service = whisper_service
        self.audio_processor = AudioProcessor(
            sample_rate=sample_rate,
            vad_mode=vad_mode,
            silence_threshold_ms=silence_threshold_ms,
            min_speech_duration_ms=min_speech_duration_ms
        )
        self.processing_queue = asyncio.Queue()
        self.is_running = False

    async def start_processing(self,
                             transcription_callback: Callable[[dict], None],
                             error_callback: Optional[Callable[[str], None]] = None):
        """
        Start processing audio segments

        Args:
            transcription_callback: Callback for transcription results
            error_callback: Callback for errors
        """
        self.is_running = True

        while self.is_running:
            try:
                # Wait for audio segment
                audio_segment = await self.processing_queue.get()

                if audio_segment is None:  # Shutdown signal
                    break

                # Transcribe with Whisper
                result = await self.whisper_service.transcribe_audio(audio_segment)

                if result and result.get("text", "").strip():
                    # Call callback as async function
                    if asyncio.iscoroutinefunction(transcription_callback):
                        await transcription_callback(result)
                    else:
                        transcription_callback(result)
                else:
                    logger.debug("No speech detected in segment")

            except Exception as e:
                error_msg = f"Processing error: {str(e)}"
                logger.error(error_msg)
                if error_callback:
                    # Call error callback as async function
                    if asyncio.iscoroutinefunction(error_callback):
                        await error_callback(error_msg)
                    else:
                        error_callback(error_msg)

    def add_audio_data(self, audio_data: bytes):
        """
        Add audio data for processing

        Args:
            audio_data: Raw audio data
        """
        segments = self.audio_processor.add_audio_chunk(audio_data)

        # Queue segments for processing
        for segment in segments:
            if len(segment) > 0:  # Only queue non-empty segments
                try:
                    self.processing_queue.put_nowait(segment)
                except asyncio.QueueFull:
                    logger.warning("Processing queue full, dropping segment")

    def force_process_current(self):
        """Force processing of current segment"""
        segment = self.audio_processor.force_segment()
        if segment is not None and len(segment) > 0:
            try:
                self.processing_queue.put_nowait(segment)
            except asyncio.QueueFull:
                logger.warning("Processing queue full, dropping forced segment")

    def stop_processing(self):
        """Stop audio processing"""
        self.is_running = False
        try:
            self.processing_queue.put_nowait(None)  # Shutdown signal
        except asyncio.QueueFull:
            pass

    def get_stats(self) -> dict:
        """Get processing statistics"""
        return {
            **self.audio_processor.get_stats(),
            "queue_size": self.processing_queue.qsize(),
            "is_running": self.is_running
        }


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """
    Convert PCM data to WAV format

    Args:
        pcm_data: Raw PCM data
        sample_rate: Sample rate
        channels: Number of channels

    Returns:
        WAV formatted audio data
    """
    output = io.BytesIO()

    with wave.open(output, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)

    return output.getvalue()


async def test_audio_processor():
    """Test function for audio processor"""
    from .whisper_service import get_whisper_service

    logger.info("Testing audio processor...")

    # Initialize services
    whisper_service = get_whisper_service()
    processor = StreamingAudioProcessor(whisper_service)

    # Test callback
    def on_transcription(result):
        print(f"Transcription: {result['text']} (Language: {result['language']})")

    def on_error(error):
        print(f"Error: {error}")

    # Start processing (would run in background)
    # processor_task = asyncio.create_task(
    #     processor.start_processing(on_transcription, on_error)
    # )

    print("Audio processor test setup complete")
    print(f"Stats: {processor.get_stats()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_audio_processor())