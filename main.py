import tkinter as tk

from clock import ClockModule
from weatherOld import WeatherModule

def main():
  root =tk.Tk()
  root.title("Smart Mirror")
  root.geometry("1920x1080")
  root.configure(bg="black")
  root.attributes("-fullscreen", True)

  root.grid_columnconfigure(0, weight=0)
  root.grid_columnconfigure(1, weight=1)
  root.grid_columnconfigure(2, weight=0)

  root.bind("<Escape>", lambda e: root.destroy())

  clock = ClockModule(root)
  clock.grid(row=0, column=1)

  weather = WeatherModule(root)
  weather.grid(row=0, column=0)

  root.mainloop()

if __name__ == '__main__':
  main()
