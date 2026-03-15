from .app import App
from .executor import Executor

executor = Executor()
app = App(executor)
app.run()
