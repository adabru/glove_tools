from typing import Callable, List


class BusSignal:
    pass


class SessionBus:
    class _Service:
        def __init__(self, name: str, obj: object):
            self.name = name
            self.obj = obj

    def __init__(self):
        self.services: List[SessionBus._Service] = []
        self.subscribers: List[Callable] = []

    def register(self, name: str, obj: object):
        self.services.append(SessionBus._Service(name, obj))

    def subscribe(self, callback: Callable):
        self.subscribers.append(callback)
