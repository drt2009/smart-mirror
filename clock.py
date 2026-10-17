import time
import tkinter as tk

class ClockModule(tk.Frame):
  def __init__(self, parent):
    super().__init__(parent)
    self.configure(bg="black")

    # Time Label
    self.time_label = tk.Label(self, text="",
                               font=("Arial", 42, "bold"),
                               fg="white", bg="black")
    self.time_label.pack()

    # Date Label
    self.date_label = tk.Label(self, text="",
                               font=("Arial", 24), fg="white",
                               bg="black")
    self.date_label.pack(pady=(5, 0))

    self.update_clock()

  def update_clock(self):
    # Format string time and date
    current_time = time.strftime("%I:%M %p")
    current_date = time.strftime("%A, %B %d")

    self.time_label.config(text=current_time)
    self.date_label.config(text=current_date)

    self.after(1000, self.update_clock)
