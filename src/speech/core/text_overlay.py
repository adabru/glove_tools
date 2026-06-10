import tkinter as tk


class TextOverlay:
    def __init__(self, default_text: str = "[default text]"):
        self.label: tk.Label | None = None
        self.initial_text = default_text

    def set_text(self, text: str) -> None:
        if self.label is not None:
            self.label.config(text=text)

    def run(self):
        self.tk_window = tk.Tk()
        self.tk_window.title("Speech App")
        self.tk_window.attributes("-fullscreen", True)
        self.tk_window.overrideredirect(True)
        self.tk_window.attributes("-topmost", True)
        self.tk_window.configure(bg="#000001")
        self.tk_window.wm_attributes("-transparentcolor", "#000001")

        self.label = tk.Label(
            self.tk_window,
            text=self.initial_text,
            font=("Segoe UI", 64, "bold"),
            fg="white",
            bg="#000001",
        )
        self.label.place(relx=0.5, rely=1.0, anchor="s")
        # self.tk_window.protocol("WM_DELETE_WINDOW", self.request_exit)
        self.tk_window.mainloop()

    def stop(self):
        if hasattr(self, "tk_window"):
            self.tk_window.after(0, self.tk_window.destroy)
