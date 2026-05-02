from tkinter import *

def mainWindow():
    window = Tk()
    window.title("Countdown Timer")
    window.geometry("400x400")
    icon = PhotoImage(file = "niga.png")
    window.iconphoto(True, icon)
    return window

def main():
    finalGUI = mainWindow()
    app = CountDownApp(finalGUI)
    finalGUI.mainloop()
    
class CountDownApp:

    def __init__(self, parentwindow):
        self.master = parentwindow

        self.canvasHeight = 200
        self.canvasWidth = 200
        self.mainCanvas = Canvas(parentwindow, height = self.canvasHeight, 
                                 width = self.canvasWidth, bg = "#0E0E0E", 
                                 borderwidth = 2)
        self.mainCanvas.pack(pady = 35, padx = 20)
        
        self.enterNumber = Entry(parentwindow, width = 14, bg ="#0E0E0E",
                                  relief = GROOVE, fg = "white")
        self.enterNumber.pack(pady = 5) 
        self.enterNumber.insert(0, "Enter a number")
        self.timerID = 0
        self.timeRemaining = 0
        self.startButton = Button(parentwindow, width = 20, bg = "#F3F3F3",
                             fg = "black", text = "Start", relief = RAISED, command = self.startCountDown)
        self.startButton.pack(pady = 15)
        self.endButton = Button(parentwindow, width = 20, bg = "#F3F3F3",
                             fg = "#0E0E0E", text = "Cancel", relief = RAISED, command = self.resetTimer)
        self.endButton.pack(pady = 5)

    def startCountDown(self):

        if self.enterNumber == "":
            print("Please enter a number to start with.")
        try:
            self.timeRemaining = int(self.enterNumber.get())
            self.startButton.config(state = "disabled")
        except ValueError:
            print("That is not a valid number.")
        self.updateTimer()
        
    def updateTimer(self):

        self.timeRemaining -= 1
        self.timerID = self.master.after(1000, self.updateTimer)
        if self.timeRemaining == 0:
            print("Times up!!!")
            self.mainCanvas.config(bg = "#00FF80")
            self.startButton.config(state = "normal")
            return
        elif self.timeRemaining > 3:
            self.mainCanvas.config(bg = "#D30000")
        elif self.timeRemaining <= 3 and self.timeRemaining >= 1:
            self.mainCanvas.config(bg = "#E68506")
        # else:
        #     print("Error")
            

    def resetTimer(self):
        self.master.after_cancel(self.timerID)
        self.timeRemaining = 0
        self.enterNumber.delete(0, "end")
        self.mainCanvas.config(bg ="#838383")
        self.startButton.config(state = "normal")
        
if __name__ == "__main__":
    main()