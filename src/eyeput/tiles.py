from dataclasses import dataclass, field

from .settings import *


@dataclass
class Action:
    label: str
    img: str


@dataclass
class InternalAction(Action):
    id: str


@dataclass
class TagAction(Action):
    tag: str
    action: str = "toggle"


@dataclass
class MouseAction(Action):
    id: str


@dataclass
class TextAction(Action):
    id: str


@dataclass
class BlinkAction(Action):
    id: str


@dataclass
class KeyAction(Action):
    pressKey: str = None

    def key(self):
        return self.pressKey or self.label


@dataclass
class ShellAction(Action):
    cmd: str = None


@dataclass
class GridLayerAction(Action):
    layer: str = None
    modifiers: set = field(default_factory=set)


tile_groups = {
    "letters": {
        "tiles": {
            "a": (KeyAction("a", None), KeyAction("shift+a", None)),
            "b": (KeyAction("b", None), KeyAction("shift+b", None)),
            "c": (KeyAction("c", None), KeyAction("shift+c", None)),
            "d": (KeyAction("d", None), KeyAction("shift+d", None)),
            "e": (KeyAction("e", None), KeyAction("shift+e", None)),
            "f": (KeyAction("f", None), KeyAction("shift+f", None)),
            "g": (KeyAction("g", None), KeyAction("shift+g", None)),
            "h": (KeyAction("h", None), KeyAction("shift+h", None)),
            "i": (KeyAction("i", None), KeyAction("shift+i", None)),
            "j": (KeyAction("j", None), KeyAction("shift+j", None)),
            "k": (KeyAction("k", None), KeyAction("shift+k", None)),
            "l": (KeyAction("l", None), KeyAction("shift+l", None)),
            "m": (KeyAction("m", None), KeyAction("shift+m", None)),
            "n": (KeyAction("n", None), KeyAction("shift+n", None)),
            "o": (KeyAction("o", None), KeyAction("shift+o", None)),
            "p": (KeyAction("p", None), KeyAction("shift+p", None)),
            "q": (KeyAction("q", None), KeyAction("shift+q", None)),
            "r": (KeyAction("r", None), KeyAction("shift+r", None)),
            "s": (KeyAction("s", None), KeyAction("shift+s", None)),
            "t": (KeyAction("t", None), KeyAction("shift+t", None)),
            "u": (KeyAction("u", None), KeyAction("shift+u", None)),
            "v": (KeyAction("v", None), KeyAction("shift+v", None)),
            "w": (KeyAction("w", None), KeyAction("shift+w", None)),
            "x": (KeyAction("x", None), KeyAction("shift+x", None)),
            "y": (KeyAction("y", None), KeyAction("shift+y", None)),
            "z": (KeyAction("z", None), KeyAction("shift+z", None)),
        },
        "width": 7,
        "height": 4,
        "color": QColor(80, 255, 255, 50),
    },
    "digits": {
        "tiles": {
            "digit7": (KeyAction("7", None), None),
            "digit8": (KeyAction("8", None), None),
            "digit9": (KeyAction("9", None), None),
            "digit4": (KeyAction("4", None), None),
            "digit5": (KeyAction("5", None), None),
            "digit6": (KeyAction("6", None), None),
            "digit1": (KeyAction("1", None), None),
            "digit2": (KeyAction("2", None), None),
            "digit3": (KeyAction("3", None), None),
            "minus": (KeyAction("-", None), KeyAction("~", None, "alt gr+~")),
            "digit0": (KeyAction("0", None), None),
            "plus": (KeyAction("+", None), KeyAction("#", None)),
        },
        "width": 3,
        "height": 4,
        "color": QColor(244, 255, 200, 50),
    },
    "navigation": {
        "tiles": {
            "backspace": (
                KeyAction("⌫", None, "backspace"),
                KeyAction("⌧", None, "delete"),
            ),
            "up": (KeyAction("⏶", None, "up"), KeyAction("⏫", None, "page up")),
            "tab": (KeyAction("⇥", None, "tab"), KeyAction("↲", None, "enter")),
            "left": (KeyAction("⏴", None, "left"), KeyAction("⏮", None, "home")),
            "down": (KeyAction("⏷", None, "down"), KeyAction("⏬", None, "page down")),
            "right": (KeyAction("⏵", None, "right"), KeyAction("⏭", None, "end")),
        },
        "width": 3,
        "height": 2,
        "color": QColor(180, 210, 255, 50),
    },
    "control": {
        "tiles": {
            "alt": (KeyAction("A", None), None),
            "ctrl": (KeyAction("C", None), None),
            "shift": (KeyAction("S", None), None),
            "win": (KeyAction("W", None), None),
            "escape": (KeyAction("❌", None, "escape"), None),
        },
        "width": 5,
        "height": 1,
        "color": QColor(255, 180, 180, 50),
    },
    "symbols": {
        "tiles": {
            # "insert": (KeyAction("⎀", None, "insert"), None),
            # "paragraph": (KeyAction("§", None, "shift+3"), None),
            "roundbrace": (
                KeyAction("(", None, "shift+("),
                KeyAction(")", None, "shift+)"),
                None,
            ),
            "squarebrace": (
                KeyAction("[", None, "alt gr+["),
                KeyAction("]", None, "alt gr+]"),
            ),
            "curlybrace": (
                KeyAction("{", None, "alt gr+{"),
                KeyAction("}", None, "alt gr+}"),
            ),
            "smaller": (KeyAction("<", None), KeyAction(">", None, "shift+>")),
            "singlequote": (
                KeyAction("'", None, "shift+numbersign"),
                KeyAction('"', None, "shift+2"),
            ),
            "backtick": (KeyAction("`", None), None),
            "pipe": (KeyAction("|", None, "alt gr+|"), KeyAction("&", None, "shift+6")),
            "dollar": (
                KeyAction("$", None, "shift+4"),
                KeyAction("€", None, "alt gr+e"),
            ),
            "dot": (KeyAction(".", None), KeyAction(":", None, "shift+:")),
            "comma": (KeyAction(",", None), KeyAction(";", None, "shift+;")),
            "questionmark": (
                KeyAction("?", None, "shift+question"),
                KeyAction("!", None, "shift+1"),
            ),
            "hat": (KeyAction("^", None), KeyAction("°", None, "shift+°")),
            "star": (KeyAction("*", None, "shift+*"), KeyAction("@", None, "alt gr+q")),
            "slash": (
                KeyAction("/", None, "shift+7"),
                KeyAction("\\", None, "alt gr+\\"),
            ),
            "perc": (KeyAction("%", None, "shift+5"), None),
            "equal": (KeyAction("=", None, "shift+="), None),
            "space": (KeyAction("⎵", None, "space"), KeyAction("_", None, "shift+_")),
        },
        "width": 4,
        "height": 6,
        "color": QColor(0, 99, 255, 50),
    },
    "frequent_context": {
        "tiles": {
            "copy": (
                KeyAction("copy", None, "ctrl+c"),
                KeyAction("paste", None, "ctrl+v"),
            ),
            "save": (KeyAction("save", None, "ctrl+s"), None),
        },
        "width": 10,
        "height": 1,
        "color": QColor(255, 60, 255, 50),
    },
    "function_keys": {
        "tiles": {
            "F1": (KeyAction("F1", None), None),
            "F2": (KeyAction("F2", None), None),
            "F3": (KeyAction("F3", None), None),
            "F4": (KeyAction("F4", None), None),
            "F5": (KeyAction("F5", None), None),
            "F6": (KeyAction("F6", None), None),
            "F7": (KeyAction("F7", None), None),
            "F8": (KeyAction("F8", None), None),
            "F9": (KeyAction("F9", None), None),
            "F10": (KeyAction("F10", None), None),
            "F11": (KeyAction("F11", None), None),
            "F12": (KeyAction("F12", None), None),
            "dot": (KeyAction(".", None), KeyAction(":", None, "shift+:")),
        },
        "width": 13,
        "height": 1,
    },
    "context": {
        "tiles": {
            "copy": (
                KeyAction("copy", None, "ctrl+c"),
                KeyAction("paste", None, "ctrl+v"),
            ),
            # "cut": (KeyAction("cut", None, "ctrl+x"), None),
            "save": (KeyAction("save", None, "ctrl+s"), None),
            "undo": (
                KeyAction("undo", None, "ctrl+z"),
                KeyAction("redo", None, "ctrl+y"),
            ),
            "clone": (
                KeyAction("clone", None, "ctrl+d"),
                KeyAction("del", None, "ctrl+shift+d"),
            ),
            "next": (KeyAction("next", None, "ctrl+alt+f"), None),
            "find": (KeyAction("find", None, "ctrl+f"), None),
        },
        "width": 8,
        "height": 4,
    },
    "eye_modes": {
        "tiles": {
            "pause_tag": (TagAction("pause", None, "pause"), None),
            "debug_gaze": (TagAction("👁", None, "debug_gaze"), None),
            "follow_tag": (TagAction("follow", None, "follow"), None),
        },
        "width": 4,
        "height": 1,
    },
    "dictation": {
        "tiles": {
            "capitalize": (TextAction("Aaa", None, "capitalize"), None),
            "point": (
                TextAction(".⎵", None, "point_space"),
                TextAction(".⎵", None, "point_newline"),
            ),
            "comma": (
                TextAction(",⎵", None, "comma_space"),
                TextAction(",⎵", None, "comma_newline"),
            ),
            "ä": (KeyAction("ä", None), KeyAction("shift+ä", None)),
            "ö": (KeyAction("ö", None), KeyAction("shift+ö", None)),
            "ü": (KeyAction("ü", None), KeyAction("shift+ü", None)),
            "ß": (KeyAction("ß", None), None),
        },
        "width": 4,
        "height": 1,
    },
    "always": {
        "tiles": {
            "scrolling_tag": (TagAction("↕", None, "scrolling"), None),
            "unpause_tag": (TagAction("unpause", None, "pause"), None),
            "follow_until_click_tag": (
                TagAction("🖰", None, "follow_until_click"),
                TagAction("follow", None, "follow"),
            ),
            "hide_labels": (
                TagAction("labels", None, "hide_labels"),
                TagAction("👁", None, "debug_gaze"),
            ),
            "disable_speech": (TagAction("🔇", None, "disable_speech"), None),
            "german": (
                TagAction("DE", None, "german"),
                TagAction("DE", None, "german_words"),
            ),
        },
        "width": 10,
        "height": 1,
        "color": QColor(80, 255, 120, 50),
    },
    "git": {
        "tiles": {
            "git_all": (TextAction("ga", None, "git_all"), None),
            "git_diff": (TextAction("gd", None, "git_diff"), None),
        },
        "width": 10,
        "height": 1,
        "color": QColor(80, 255, 120, 50),
    },
}
tiles = {
    "keyboard1": {
        "letters": (0, 0),
        "digits": (11, 0),
        "navigation": (11, 4),
        "control": (0, 4),
        "symbols": (7, 0),
        "frequent_context": (9, 4),
    },
    "keyboard2": {"function_keys": (0, 0)},
    "textCmds": {"context": (0, 0)},
    "dictation": {
        "dictation": (0, 0),
        "git": (1, 3),
    },
    # "apps": {
    #     # row 0
    #     "vsc-eyeput": (ShellAction(None),
    #         "/eyeput",
    #         f"{os.path.dirname(__file__)}/resources/vsc.png",
    #         1,
    #         0,
    #         f"code {os.path.dirname(__file__)}",
    #     ),
    #     # row 1
    #     "terminal": (ShellAction(None),
    #         "",
    #         "/usr/share/app-info/icons/archlinux-arch-community/128x128/liri-terminal_utilities-terminal.png",
    #         0,
    #         1,
    #         "gnome-terminal",
    #     ),
    #     # row 2
    #     "google": (ShellAction(None),
    #         "google",
    #         "/usr/share/app-info/icons/archlinux-arch-extra/64x64/kaccounts-providers_applications-internet.png",
    #         0,
    #         2,
    #         "xdg-open http://google.com &",
    #     ),
    #     "golem": (ShellAction(None),
    #         "golem",
    #         f"{os.path.dirname(__file__)}/resources/jitsi.png",
    #         1,
    #         2,
    #         "xdg-open https://meet.golem.de/ &",
    #     ),
    #     "github": (ShellAction(None),
    #         "github",
    #         f"{os.path.dirname(__file__)}/resources/web-github-icon.png",
    #         2,
    #         2,
    #         "xdg-open https://github.com/adabru &",
    #     ),
    #     "github": (ShellAction(None),
    #         "github",
    #         "invalid path",
    #         2,
    #         3,
    #         "xdg-open https://github.com/adabru &",
    #     ),
    # },
    "eye_modes": {"eye_modes": (0, 0)},
    "empty": {},
    "always": {"always": (0, 5)},
}


@dataclass(frozen=True)
class Zone:
    top_left: tuple[float, float]
    bottom_right: tuple[float, float]

    def __contains__(self, point):
        return (
            self.top_left[0] <= point[0] <= self.bottom_right[0]
            and self.top_left[1] <= point[1] <= self.bottom_right[1]
        )


Zone.tl = Zone((-0.1, -0.1), (0.3, 0.3))
Zone.l = Zone((-0.1, 0.3), (0.3, 0.6))
Zone.tr = Zone((0.7, -0.1), (1.1, 0.3))
Zone.br = Zone((0.7, 0.7), (1.1, 1.1))
Zone.r = Zone((0.7, 0.3), (1.1, 0.6))
Zone.c = Zone((0.3, 0.3), (0.6, 0.6))
Zone.inside = Zone((-0.1, -0.1), (1.1, 1.1))
Zone.any = Zone((-100.0, -100.0), (100.0, 100.0))

# commands further up have precedence
blink_commands = {
    "tag_cursor": {
        (".", Zone.any): BlinkAction("", None, "mouse_stop_move"),
    },
    "tag_calibration": {
        (". . .", Zone.any): BlinkAction("", None, "calibration_cancel"),
        (". .", Zone.any): BlinkAction("", None, "calibration_next"),
    },
    "tag_pause": {
        (".r", Zone.inside): BlinkAction("", None, "select_and_hold"),
        (".l", Zone.inside): BlinkAction("", None, "select_and_hold"),
    },
    "tag_grid": {
        (" ", Zone.any): TagAction("↕", None, "grid", "unset"),
        (".r", Zone.inside): BlinkAction("", None, "select_0"),
        (".l", Zone.inside): BlinkAction("", None, "select_1"),
    },
    "tag_scrolling": {
        (". r", Zone.inside): BlinkAction("", None, "scroll_up"),
        (" r", Zone.inside): BlinkAction("", None, "scroll_up"),
        (". l", Zone.inside): BlinkAction("", None, "scroll_down"),
        (" l", Zone.inside): BlinkAction("", None, "scroll_down"),
        (" ", Zone.any): BlinkAction("", None, "scroll_stop"),
        (".", Zone.any): BlinkAction("", None, "scroll_stop"),
    },
    "default": {
        (".r", Zone.c): GridLayerAction("", None, "keyboard1"),
        (".l", Zone.c): GridLayerAction("", None, "keyboard1", ("shift",)),
        (".r", Zone.l): GridLayerAction("", None, "keyboard1", ("ctrl",)),
        (".l", Zone.l): GridLayerAction("", None, "keyboard1", ("ctrl", "shift")),
        (".r", Zone.tr): GridLayerAction("", None, "keyboard2"),
        (".r", Zone.br): GridLayerAction("", None, "textCmds"),
        (".r", Zone.r): GridLayerAction("", None, "dictation"),
        (".r", Zone.tl): GridLayerAction("", None, "eye_modes"),
        (".r", Zone.inside): BlinkAction("", None, "select_0"),
        (".l", Zone.inside): BlinkAction("", None, "select_1"),
    },
}
