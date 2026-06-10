#!/usr/bin/env python3


import logging

from .core.app import App, Command, DictationCallback
from .user.default_commands import DefaultCommands


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    app = App()
    app_state = app.get_state()
    default_commands = DefaultCommands(app_state)
    for command in default_commands.get_commands():
        if isinstance(command, Command):
            app.register_command(command)
        elif isinstance(command, DictationCallback):
            app.register_dictation_callback(command)
    app.run()


if __name__ == "__main__":
    main()
