import logging
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread
from typing import Callable

from speech.core.event_queue import EventQueue
from speech.core.speech_service import SpeechMode, SpeechService
from speech.core.text_overlay import TextOverlay


@dataclass
class Command:
    command: str
    callback: Callable


@dataclass
class DictationCallback:
    callback: Callable[[str], None]


@dataclass
class AppState:
    """Expose the current state of the app to the command callbacks, so that they can modify it if needed."""

    get_speech_service: Callable[[], SpeechService | None]
    request_exit: Callable[[], None]


class App:
    # documentation for vosk:
    # https://github.com/alphacep/vosk-api/tree/master/python/example
    def __init__(self):
        self.speech_service: SpeechService | None = None
        self.commands: list[Command] = []
        self.dictation_callbacks: list[DictationCallback] = []
        self.text_overlay: TextOverlay | None = None
        self.event_queue = EventQueue()

    def get_state(self) -> AppState:
        return AppState(
            get_speech_service=lambda: self.speech_service,
            request_exit=self.request_exit,
        )

    def request_exit(self) -> None:
        if self.speech_service is not None:
            self.speech_service.stop()
        if self.text_overlay is not None:
            self.text_overlay.stop()
        self.event_queue.stop()

    def _run_worker(
        self, target: Callable[[], None], thread_errors: Queue[BaseException]
    ) -> None:
        try:
            target()
        except Exception as exc:
            thread_errors.put(exc)
            self.request_exit()

    def _raise_worker_error_if_any(self, thread_errors: Queue[BaseException]) -> None:
        try:
            exc = thread_errors.get_nowait()
        except Empty:
            return
        raise exc

    def on_command_phrase_recognized(self, phrase: str) -> None:
        for command in self.commands:
            if phrase.startswith(command.command):
                logging.info(f"Executing command: {command.command}")
                command.callback()
                break

    def on_dictate_result(self, text: str) -> None:
        logging.info(f"Dictated text: {text}")
        for callback in self.dictation_callbacks:
            callback.callback(text)

    def on_partial_result(self, text: str) -> None:
        if self.text_overlay is not None and text.strip() != "":
            self.text_overlay.set_text(text)

    def on_mode_switched(self, mode: SpeechMode) -> None:
        if self.text_overlay is not None:
            self.text_overlay.set_text(f"[{mode.name}]")

    def wrap(self, func: Callable) -> Callable:
        """Wrap a function so that it can be safely called from another thread and its result will be processed in the main thread."""

        def wrapped_func(*args, **kwargs):
            self.event_queue.wrap_func(func)(*args, **kwargs)

        return wrapped_func

    def run(self):
        self.text_overlay = TextOverlay(f"[{SpeechMode.COMMAND.name}]")
        self.speech_service = SpeechService(
            command_phrases=[command.command for command in self.commands],
            on_command_phrase_recognized=self.wrap(self.on_command_phrase_recognized),
            on_dictate_result=self.wrap(self.on_dictate_result),
            on_partial_result=self.wrap(self.on_partial_result),
            on_mode_switched=self.wrap(self.on_mode_switched),
        )
        speech_service = self.speech_service
        text_overlay = self.text_overlay
        assert speech_service is not None
        assert text_overlay is not None
        try:
            thread_errors: Queue[BaseException] = Queue()
            speech_service_thread = Thread(
                target=lambda: self._run_worker(speech_service.run, thread_errors),
                daemon=True,
            )
            speech_service_thread.start()
            text_overlay_thread = Thread(
                target=lambda: self._run_worker(text_overlay.run, thread_errors),
                daemon=True,
            )
            text_overlay_thread.start()
            speech_service.set_speech_mode(SpeechMode.COMMAND)
            self.event_queue.run()
            self._raise_worker_error_if_any(thread_errors)
        except KeyboardInterrupt:
            logging.info("\nApp terminated by user")
            self.request_exit()

    def register_command(self, command: Command) -> None:
        self.commands.append(command)

    def register_dictation_callback(self, callback: DictationCallback) -> None:
        self.dictation_callbacks.append(callback)
