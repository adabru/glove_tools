import enum
import json
import logging
from dataclasses import dataclass
from threading import Event, Thread
from typing import Callable

# https://github.com/daanzu/py-webrtcvad-wheels
import webrtcvad

# https://github.com/alphacep/vosk-api/tree/master/python/example
from vosk import KaldiRecognizer, Model

from speech.core.microphone import Microphone


class SpeechMode(enum.Enum):
    COMMAND = 1
    DICTATE = 2
    SLEEP = 3


SMALL_MODEL_PATH = "./vosk_model/vosk-model-small-de-0.15"
LARGE_MODEL_PATH = "./vosk_model/vosk-model-de-0.21"

# wideband, used by Vosk models and webrtcvad
SAMPLE_RATE = 16000
SAMPLE_SIZE = 2  # 16 bit audio
VAD_FRAME_DURATION = (
    0.02  # 20 ms frames for VAD, webrtcvad supports 10, 20 or 30 ms frames
)
MIC_FRAME_DURATION = 0.3
MIC_FRAME_SIZE = int(SAMPLE_RATE * MIC_FRAME_DURATION) * SAMPLE_SIZE
VAD_FRAME_SIZE = int(SAMPLE_RATE * VAD_FRAME_DURATION) * SAMPLE_SIZE
VAD_START_THRESHOLD_RATIO = 0.3


class SpeechService:

    @dataclass
    class _RunState:
        last_speech_mode: SpeechMode = SpeechMode.SLEEP
        last_mic_frame: bytes = bytes()

        consumed: str = ""
        buffer: str = ""
        clear: bool = False
        wait_for_word_end: bool = True
        wait_for_voice_activity_start: bool = True

        def reset_mode(self):
            self.consumed = ""
            self.buffer = ""
            self.clear = False
            self.wait_for_word_end = True
            self.wait_for_voice_activity_start = True

    def __init__(
        self,
        command_phrases: list[str],
        on_command_phrase_recognized: Callable[[str], None],
        on_dictate_result: Callable[[str], None],
        on_partial_result: Callable[[str], None],
        on_mode_switched: Callable[[SpeechMode], None] | None = None,
    ):
        assert (
            len(command_phrases) > 0
        ), "At least one command must be registered before running the app"
        self._speech_mode = SpeechMode.SLEEP
        self._command_phrases = command_phrases
        self._on_command_phrase_recognized = on_command_phrase_recognized
        self._on_dictate_result = on_dictate_result
        self._on_partial_result = on_partial_result
        self._on_mode_switched = on_mode_switched
        self._small_model_command_recognizer: KaldiRecognizer | None = None
        self._large_model_dictate_recognizer: KaldiRecognizer | None = None
        self._vad: webrtcvad.Vad | None = None

        self._large_model_thread: Thread | None = None
        """Handle for the thread that initializes the large model, so that it can be joined on app shutdown to ensure proper cleanup."""
        self._small_model: Model | None = None
        """Cache the small model so that it doesn't have to be loaded multiple times for command and dictate recognizers."""
        self._command_recognizer: KaldiRecognizer | None = None
        """Active recognizer for commands, always uses the small model for faster response time."""
        self._dictate_recognizer: KaldiRecognizer | None = None
        """Active recognizer for dictation, fast start with small model, transition to large model when it finished loading."""
        self._stop_event = Event()
        """Event to signal the speech service to stop."""

    def get_speech_mode(self) -> SpeechMode:
        return self._speech_mode

    def set_speech_mode(self, mode: SpeechMode) -> None:
        self._speech_mode = mode
        if self._on_mode_switched is not None:
            self._on_mode_switched(mode)

    def _init_small_model_dictate_recognizer(self, samplerate: int) -> None:
        """Initializing the small model takes around 2 seconds."""
        if self._small_model is None:
            self._small_model = Model(SMALL_MODEL_PATH)
        self.small_model_dictate_recognizer = KaldiRecognizer(
            self._small_model, samplerate
        )
        self._dictate_recognizer = self.small_model_dictate_recognizer
        logging.info("Small model dictate initialized.")

    def _init_small_model_command_recognizer(self, samplerate: int) -> None:
        """Initializing the small model takes around 2 seconds."""
        if self._small_model is None:
            self._small_model = Model(SMALL_MODEL_PATH)
        model_small = self._small_model
        word_list = json.dumps(self._command_phrases + ["[unk]"], ensure_ascii=False)
        self._small_model_command_recognizer = KaldiRecognizer(
            model_small, samplerate, word_list
        )
        # some commands might be interrupted while speaking, so we also want to get partial results
        # rec.SetGrammar(word_list)
        self._command_recognizer = self._small_model_command_recognizer
        logging.info("Small model command initialized.")

    def _init_large_model_dictate_recognizer(self, samplerate: int) -> None:
        """Initializing the large model takes around 60 seconds."""
        large_model = Model(LARGE_MODEL_PATH)
        self._large_model_dictate_recognizer = KaldiRecognizer(large_model, samplerate)
        logging.info("Large model dictate initialized.")

    def _start_large_model_init(self, samplerate: int) -> None:
        """Start initializing the large model in a separate thread so that main thread can already start listening for commands with the small model."""
        self._large_model_thread = Thread(
            target=self._init_large_model_dictate_recognizer,
            args=(samplerate,),
            daemon=True,
        )
        self._large_model_thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _detect_voice_activity(
        self, data: bytes, samplerate: int, frame_size: int
    ) -> list[bool]:
        """Detect voice activity in the given audio data using webrtcvad."""
        if self._vad is None:
            self._vad = webrtcvad.Vad(3)
        assert (
            len(data) >= frame_size
        ), "Audio data chunk is smaller than VAD frame size"
        activity = []
        offset = 0
        while offset + frame_size <= len(data):
            frame = data[offset : offset + frame_size]
            offset += frame_size
            is_speech = self._vad.is_speech(frame, samplerate)
            activity.append(is_speech)
        return activity

    def _process_frame_in_command_mode(
        self, mic_frame: bytes, state: _RunState
    ) -> None:
        assert self._command_recognizer is not None
        # when switching to command mode, wait for the start of voice activity to avoid getting erratic partial results
        if state.wait_for_voice_activity_start:
            voice_activity = self._detect_voice_activity(
                mic_frame, SAMPLE_RATE, VAD_FRAME_SIZE
            )
            speech_frame_count = sum(voice_activity)
            if speech_frame_count / len(voice_activity) < VAD_START_THRESHOLD_RATIO:
                return  # not enough voice activity yet, keep waiting
            logging.debug(
                f"Voice activity detected {speech_frame_count}/{len(voice_activity)} frames"
            )
            state.wait_for_voice_activity_start = False
            # feed last mic frame again to recognizer so that the beginning of the command is not cut off
            self._command_recognizer.AcceptWaveform(state.last_mic_frame)
        if self._command_recognizer.AcceptWaveform(mic_frame):
            result = json.loads(self._command_recognizer.Result())
            state.buffer = result["text"]
            state.clear = True
        else:
            result = json.loads(self._command_recognizer.PartialResult())
            state.buffer = result["partial"]
        self._on_partial_result(state.buffer)
        unconsumed = state.buffer[len(state.consumed) :]
        if len(unconsumed) > 0:
            for command_phrase in self._command_phrases:
                if unconsumed.startswith(command_phrase):
                    logging.debug(f"Command phrase recognized: {command_phrase}")
                    self._on_command_phrase_recognized(command_phrase)
                    state.consumed += command_phrase + " "
                    break
        if state.clear:
            state.reset_mode()

    def _process_frame_in_dictate_mode(
        self, mic_frame: bytes, state: _RunState
    ) -> None:
        assert self._dictate_recognizer is not None
        # if the user switches to dictate mode and the large model is already initialized, use it for better accuracy
        if (
            self._large_model_dictate_recognizer is not None
            and self._dictate_recognizer != self._large_model_dictate_recognizer
        ):
            self._dictate_recognizer = self._large_model_dictate_recognizer
            logging.info(f"Switched to large model for dictation.")
        # when switching to dictate mode, wait for the end of the currently spoken word before starting to listen for dictation, to avoid getting partial results of the command as dictate results
        if state.wait_for_word_end:
            # discard the rest of the last word before starting dictation
            voice_activity = self._detect_voice_activity(
                mic_frame, SAMPLE_RATE, VAD_FRAME_SIZE
            )
            first_non_speech_index = next(
                (i for i, is_speech in enumerate(voice_activity) if not is_speech),
                None,
            )
            if first_non_speech_index is None:
                return  # still all speech, keep waiting
            logging.debug("End of word detected, starting dictation")
            mic_frame = mic_frame[first_non_speech_index * VAD_FRAME_SIZE :]
            state.wait_for_word_end = False
        if self._dictate_recognizer.AcceptWaveform(mic_frame):
            result = json.loads(self._dictate_recognizer.Result())
            text = result["text"]
            logging.debug(f"Dictated text: {text}")
            self._on_dictate_result(text)
            self.set_speech_mode(SpeechMode.COMMAND)
        else:
            result = json.loads(self._dictate_recognizer.PartialResult())
            text = result["partial"]
            logging.debug(f"Partial dictate result: {text}")
        self._on_partial_result(text)

    def run(self):
        mic = Microphone(SAMPLE_RATE)
        self._init_small_model_command_recognizer(SAMPLE_RATE)
        self._init_small_model_dictate_recognizer(SAMPLE_RATE)
        self._start_large_model_init(SAMPLE_RATE)
        state = self._RunState()
        logging.info("Listening...")
        for mic_frame in mic.record(MIC_FRAME_SIZE):
            if self._stop_event.is_set():
                logging.info("Stopping speech service...")
                break

            if self._speech_mode != state.last_speech_mode:
                state.reset_mode()
                assert self._command_recognizer is not None
                self._command_recognizer.Reset()
                assert self._dictate_recognizer is not None
                self._dictate_recognizer.Reset()

            if self._speech_mode == SpeechMode.SLEEP:
                pass
            elif self._speech_mode == SpeechMode.COMMAND:
                self._process_frame_in_command_mode(mic_frame, state)
            elif self._speech_mode == SpeechMode.DICTATE:
                self._process_frame_in_dictate_mode(mic_frame, state)

            state.last_mic_frame = mic_frame
            state.last_speech_mode = self._speech_mode
