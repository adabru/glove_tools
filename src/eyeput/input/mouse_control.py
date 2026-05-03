# https://github.com/moses-palmer/pynput

from pynput import mouse

from eyeput.input.input_control import InputControl, InputControlProvider
from eyeput.input.input_type import InputVector2


class MouseControl(InputControlProvider):
    def __init__(self):
        self.controller = mouse.Controller()
        self.multiplier = (1.0, 1.0)

    def get_mouse_position(self) -> InputVector2:
        assert (
            self.multiplier is not None
        ), "Screen size must be set before getting mouse position"
        x, y = self.controller.position
        x *= self.multiplier[0]
        y *= self.multiplier[1]
        return InputVector2(x, y)

    def set_multiplier(self, width_multiplier: float, height_multiplier: float):
        self.multiplier = (width_multiplier, height_multiplier)

    def get_input_controls(self) -> list[InputControl]:
        return [
            InputControl(
                "mouse_vector2",
                InputVector2,
                get_value_func=self.get_mouse_position,
            )
        ]
