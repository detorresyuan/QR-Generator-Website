from tkinter import *
from PIL import Image, ImageTk # used to load images and create an object for image data
import cv2 #for computer vision and image processing
import random

def mainWindow():
    window = Tk()
    window.geometry("525x525")
    window.title("Meme It Monke")
    icon = PhotoImage(file = "niga.png")
    window.iconphoto(True, icon)
    return window

def main():
    finalGUI = mainWindow()
    app = MemeItMonke(finalGUI)
    finalGUI.mainloop()

class MemeItMonke:
    memeLists = ["uha.png", "hmm.png", "uhh.png"] #array of images used from PIL
    def __init__(self, parentwindow):
        self.master = parentwindow

        self.photoimage = [] #where the converted image will go

        for filename in self.memeLists: #convert each file in the array and resizes for the canvas
            cvImage = cv2.imread(filename)#process an image to numerical format for numpy array(height, width, channels)
            cvImage = cv2.resize(cvImage, (400, 400))
            cvImageRGB = cv2.cvtColor(cvImage, cv2.COLOR_BGR2RGB)# converts from BGR(Blue green red) into RGB (Red Green Blue)
            pilImage = Image.fromarray(cvImageRGB)# bridges the gap from opencv to pillow, meaning access the coverted numerical data into images
            photo = ImageTk.PhotoImage(pilImage)#Converts the now Pillow image into an image that tkinter can output
            self.photoimage.append(photo)#append adds a new single item at the end of a list

        self.canvasHeight = 400
        self.canvasWidth = 400
        self.mainCanvas = Canvas(parentwindow, width = self.canvasWidth, 
                            height = self.canvasHeight, bg = "#292727",
                            borderwidth = 2)
        self.mainCanvas.pack(pady = 35, padx = 20)
        self.mainButton = Button(parentwindow, width = 20, relief = RAISED, bg = "#FFFFFF", 
                                 text = "MONKE", fg = "#292727", command = self.imageRandomizer)
        self.mainButton.pack(pady = 2)
    
    def imageRandomizer(self):
        self.pickedMeme = random.choice(self.photoimage)
        self.master.myImage = self.pickedMeme
        self.mainCanvas.create_image(self.canvasHeight // 2, 
                                     self.canvasWidth // 2, 
                                     image = self.pickedMeme,
                                     anchor = CENTER)#this draws a specific image into a widget and where will it be placed
    
if __name__ == "__main__":
    main()

