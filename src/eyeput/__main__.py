from .ui.app import App
from .ui.executor import Executor

executor = Executor()
app = App(executor)
app.run()
