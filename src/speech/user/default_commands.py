import logging
import subprocess
import time

# https://github.com/moses-palmer/pynput
from pynput import keyboard

from speech.core.app import AppState, Command, DictationCallback
from speech.core.speech_service import SpeechMode
from speech.user.german import GermanFormatter


class DefaultCommands:
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.german_formatter = GermanFormatter()
        self.german_formatter.load()
        self.keyboard_controller = keyboard.Controller()

    def type(self, text: str):
        # activate keyboard
        self.keyboard_controller.press(keyboard.Key.shift)
        self.keyboard_controller.release(keyboard.Key.shift)
        time.sleep(0.02)
        self.keyboard_controller.type(text)

    def open_youtube(self):
        subprocess.run(["start", "https://www.youtube.com"], shell=True)

    def open_file_manager(self):
        subprocess.run(["start", "explorer"], shell=True)

    def close_app(self):
        logging.info("Closing app...")
        self.app_state.request_exit()

    def start_dictation(self):
        speech_service = self.app_state.get_speech_service()
        assert (
            speech_service is not None
        ), "SpeechService must be initialized before dictation can be activated"
        speech_service.set_speech_mode(SpeechMode.DICTATE)

    def start_sleep(self):
        speech_service = self.app_state.get_speech_service()
        assert (
            speech_service is not None
        ), "SpeechService must be initialized before sleep mode can be activated"
        speech_service.set_speech_mode(SpeechMode.SLEEP)

    def dictate(self, text: str):
        formatted_text = self.german_formatter.format(text)
        self.type(formatted_text)

    def type_key(self, key: keyboard.Key):
        self.keyboard_controller.press(key)
        self.keyboard_controller.release(key)

    def get_commands(self) -> list[Command | DictationCallback]:
        return [
            Command("öffne youtube", self.open_youtube),
            Command("öffne dateimanager", self.open_file_manager),
            Command("beenden", self.close_app),
            Command("schreibe", self.start_dictation),
            Command("eingabe", lambda: self.type_key(keyboard.Key.enter)),
            Command("einschlafen", self.start_sleep),
            DictationCallback(self.dictate),
        ]
