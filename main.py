import tkinter as tk

from clock import ClockModule
from weather.module import WeatherModule
from agenda.module import AgendaModule
import config

def main():
  root =tk.Tk()
  root.title("Smart Mirror")
  root.geometry("1920x1080")
  root.configure(bg="black")
  root.configure(cursor="none")
  root.attributes("-fullscreen", True)

  for column in range(3):
    root.grid_columnconfigure(column, weight=1, uniform="thirds")
  root.grid_rowconfigure(0, weight=0)
  root.bind("<Escape>", lambda e: root.destroy())

  clock = ClockModule(root)
  clock.grid(row=0, column=1, sticky="n")

  (lat,lon) = config.load_location()
  location_name = config.load_location_name()
  weather = WeatherModule(root,lat,lon,location_name)
  weather.grid(row=0, column=0, sticky="nw")

  ical_address = config.load_calendar_url()
  agenda = AgendaModule(root,ical_address)
  agenda.grid(row=0, column=2, sticky="ne")


  root.mainloop()

if __name__ == '__main__':
  main()
