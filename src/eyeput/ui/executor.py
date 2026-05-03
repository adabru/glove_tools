import time

from .. import external


class Executor:
    def execute(self, id: str, data: object = None):
        if id == "capitalize":
            external.press_key("ctrl+c")
            time.sleep(0.03)
            s: str = external.get_clipboard()
            s = s.capitalize()
            time.sleep(0.03)
            external.set_clipboard(s)
            time.sleep(0.03)
            external.press_key("ctrl+v")
        elif id == "point_space":
            external.press_key(".")
            external.press_key(" ")
        elif id == "point_newline":
            external.press_key(".")
            external.press_key("enter")
        elif id == "comma_space":
            external.press_key(",")
            external.press_key(" ")
        elif id == "comma_newline":
            external.press_key(",")
            external.press_key("enter")
        elif id == "git_diff":
            external.type("git diff --ws-error-highlight=all\n")
        elif id == "git_all":
            external.type("git add -A\n")
        # if id == "left_click":
        #     external.left_click()
