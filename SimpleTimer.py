from tkinter import *


def mainWindow():
    window = Tk()
    window.geometry("300x225")
    window.title("simple timer")
    icon = PhotoImage(file = "uha.png")
    window.iconphoto(True, icon)
    return window
def main():
    finalGUI = mainWindow()
    app = SimpleTimer(finalGUI)
    finalGUI.mainloop()

class SimpleTimer:
    def __init__(self, parentwindow):
        self.master = parentwindow
        canvasW = 250
        canvasH = 100
        self.startButtonColor = "#59E086"
        self.resetButtonColor = "#EC3030"
        self.mainCanvas = Canvas(parentwindow, width = canvasW, height = canvasH, bg = "#E2E2E2")
        self.mainCanvas.pack(pady = 10, padx = 10)

        self.enterNumber = Entry(parentwindow, width = 19, bg = "#FFFFFF")
        self.enterNumber.pack(pady = 5)
        self.enterNumber.insert(0, "enter time in seconds")
        
        self.startButton = Button(parentwindow, fg = "#000000", bg = "#F3F3F3", 
                                  width = 15, text = "Start Timer", relief = RAISED, command = self.timeModule)
        self.startButton.pack(pady = 5)
        self.resetButton = Button(parentwindow, fg = "#000000", bg = "#F3F3F3", 
                                  width = 15, text = "Reset Timer", relief = RAISED, command = self.resetTimer)
        self.resetButton.pack(pady = 5)

        self.myTime = int(input("Enter a desired time in seconds: "))
        self.countdown_id = None
        self.remaining_time = 0

    def timeModule(self):
        if self.enterNumber.get() == "":
            print("Please enter a number to start with.")
            return
        try:
            self.myTime = int(self.enterNumber.get())
            self.startButton.config(state = "disabled", bg = self.startButtonColor)
        except ValueError:
            print("That is not a valid number.")
            return
        
        self.remaining_time = self.myTime
        self.countdown_tick()

    def countdown_tick(self):
        if self.remaining_time <= 0:
            self.print("Times Up!!!")
            return
        
        self.minutes = int(self.remaining_time / 60) % 60
        self.hours = int(self.remaining_time / 3600)
        self.seconds = self.remaining_time % 60

        self.print(f"{self.hours:02}:{self.minutes:02}:{self.seconds:02}")
        self.remaining_time -= 1
        self.countdown_id = self.mainCanvas.after(1000, self.countdown_tick)

    def resetTimer(self):
        if self.countdown_id:
            self.mainCanvas.after_cancel(self.countdown_id)
            self.countdown_id = None
        self.remaining_time = 0
        self.mainCanvas.delete("all")
        self.startButton.config(state = "normal")

    def print(self, *args, **kwargs):
        self.mainCanvas.delete("all")
        self.mainCanvas.create_text(125, 50, text = args[0], font = ("Helvetica", 24), fill = "#000000")
        
if __name__ == "__main__":
    main()