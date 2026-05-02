from tkinter import *
import math

colors = ["#DFDFDF","#5C24F3","#2BE75A", "#EC2323", "#E2F10E","#302A2A"] # make a array outside the function

def colorChange(colorName, colorWidget): # define the names to output in print

    print(f"Your Color is {colorName} ")
    colorWidget.config(bg = colorName)

window = Tk() #create a window
window.title("Color Picker 9000")
# icon = PhotoImage(file = "Screenshot 2025-10-03 223520.png")
# window.iconphoto(True, icon)
    
canvasHeight = 900 # establish the dimensions
canvasWitdh = 700
mainFrame = Frame(window, padx = 20, pady = 20, relief= GROOVE, borderwidth = 2, bg="gray") #optional create a frame
mainFrame.pack(fill="both", expand= True, pady = (0, 200))
mainCanvas = Canvas(mainFrame, height= canvasHeight, width = canvasWitdh, # create a canvas
                                        borderwidth = 2, bg = "white")
mainCanvas.pack(pady = 20, padx = 20)    

xPosition = 100 # where the buttons will go
spacing = 50  # amount of space between buttons

for i, bgColor in enumerate(colors): # create for loop for the array and use enumerate from 0
                                     #untill the max which in this case 6
    buttonColor = Button(
        window, width = 40, bg = bgColor,
        fg = "grey", relief = RAISED
    )
    buttonColor.config( # configure the buttons to have function using command lambda and esthablish what it does using
        command = lambda c = bgColor : colorChange(c, mainCanvas) #defined colorchanger, and where it outputs
    )
    mainCanvas.create_window( # create the window
        canvasWitdh / 2,
        xPosition,
        window = buttonColor,
        anchor = N # where it is, north, south, west or east
    )
    xPosition += spacing # where the buttons will go plus its spacings

        # self.button1 = Button(parentWindow, bg = "white", bd = 40, command = lambda: self.colorButton1)
        # self.button1.place(x = 1000, y = 500)
        # self.button2 = Button(parentWindow, bg = "blue", bd = 40, command = lambda: self.colorButton2)
        # self.button2.place(x = 900, y = 500) 
        # self.button3 = Button(parentWindow, bg = "green", bd = 40, command = lambda: self.colorButton3)  
        # self.button3.place(x = 800, y = 500)        
        # self.button4 = Button(parentWindow, bg = "red", bd = 40, command = lambda: self.colorButton4)
        # self.button4.place(x = 550, y = 500)
        # self.button5 = Button(parentWindow, bg = "yellow", bd = 40, command = lambda: self.colorButton5)
        # self.button5.place(x = 450, y = 500)
        # self.button6 = Button(parentWindow, bg = "black", bd = 40, command = lambda: self.colorButton6)
        # self.button6.place(x = 350, y = 500)  
finalGUI = window    
finalGUI.mainloop() # outputs it in the window

