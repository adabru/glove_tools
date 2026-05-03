from typing import Callable, List, Set


class Event:
    listeners: List[Callable[..., None]]
    muted: Callable[..., None] | None

    def __init__(self):
        self.listeners = []
        self.muted = None

    def notify(self, *args):
        for callback in self.listeners:
            if callback == self.muted:
                self.muted = None
            else:
                callback(*args)

    def subscribe(self, callback: Callable):
        self.listeners.append(callback)

    def mute_once(self, callback: Callable):
        self.muted = callback


class Tags:
    tags: Set[str]
    tag_changed: Event

    def __init__(self):
        self.tags = set()
        self.tag_changed = Event()

    def __iter__(self):
        return iter(self.tags)

    def has(self, tag: str):
        return tag in self.tags

    def get_tags(self):
        return self.tags

    def set_tag_value(self, tag: str, value: bool):
        if value:
            self.set_tag(tag)
        else:
            self.unset_tag(tag)

    def set_tag(self, tag: str):
        self.tags.add(tag)
        self.tag_changed.notify(tag, True)

    def unset_tag(self, tag: str):
        self.tags.discard(tag)
        self.tag_changed.notify(tag, False)

    def toggle_tag(self, tag: str):
        if tag in self.tags:
            self.unset_tag(tag)
        else:
            self.set_tag(tag)
