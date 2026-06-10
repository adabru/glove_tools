import queue


class EventQueue:
    """A wrapper around queue.Queue to decouple the producer and consumer of events."""

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()

    def wrap_func(self, func):
        """Wrap a function so that it can be safely called from another thread and its result will be processed in the main thread."""

        def wrapped_func(*args, **kwargs):
            self._queue.put((func, args, kwargs))

        return wrapped_func

    def run(self):
        """Run the event loop, processing events from the queue."""
        while True:
            func, args, kwargs = self._queue.get()
            if func is None:
                break
            func(*args, **kwargs)

    def stop(self):
        """Stop the event loop by putting a special event in the queue."""
        self._queue.put((None, (), {}))
