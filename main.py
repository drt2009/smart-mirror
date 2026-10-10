import tkinter as tk

from clock import ClockModule

#For Weather



def main():
  root =tk.Tk()
  root.title("Smart Mirror")
  root.geometry("1920x1080")
  root.configure(bg="black")
  root.attributes("-fullscreen", True)

  root.bind("<Escape>", lambda e: root.destroy())

  clock = ClockModule(root)
  clock.pack()

  root.mainloop()

if __name__ == '__main__':
  main()
