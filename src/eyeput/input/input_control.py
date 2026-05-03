from typing import Callable


class InputControl:
    """Class representing an input control, such as a button, axis, trigger, or vector2."""

    def __init__(
        self,
        name: str,
        control_type: type,
        get_value_func: Callable | None = None,
        value=None,
    ):
        self.name = name
        self.control_type = control_type
        self.value = value
        self.get_value_func = get_value_func

    def get_value(self):
        """Update the value of the control."""
        if self.get_value_func is not None:
            self.value = self.get_value_func()
        return self.value


class InputControlProvider:
    """Interface for classes that provide input controls."""

    def get_input_controls(self) -> list[InputControl]:
        """Return a list of input controls provided by this class."""
        raise NotImplementedError
