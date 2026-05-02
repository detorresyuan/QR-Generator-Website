from tkinter import *
import random
import math
import tkinter as tk

# --- 1. File Loading (Moved to function for clean use) ---
def load_values(filename="values.txt"):
    """Reads values from the file and returns a list."""
    try:
        with open(filename, "r") as f:
            rawValue = f.readlines()
            masterValues = [basicValue.strip() for basicValue in rawValue if basicValue.strip()]
            return masterValues
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return ["Error 1", "Error 2", "Error 3", "Error 4"] # Fallback values

# --- 2. Window Setup (Modified to remove missing icon file) ---
def create_window():
    """Sets up and returns the root Tkinter window."""
    windowCoco = Tk()
    # Adjusted geometry to better fit the canvas size + padding
    windowCoco.geometry('600x650') 
    windowCoco.config(bg='black')
    windowCoco.title('Animated Wheel of Skibs')
    # Icon photo removed as the file is not available
    return windowCoco

class RouletteApp:

    def __init__(self, parentWindow, masterValues):
        self.master = parentWindow
        
        # --- 1. Load Data and Dimensions (Now instance variables) ---
        self.masterValues = masterValues
        self.N = len(masterValues)
        self.canvasSize = 500
        self.centerX = self.canvasSize / 2
        self.centerY = self.canvasSize / 2
        self.raduis = 200      
        self.textRaduis = 150 
        self.segmentAngle = 360.0 / self.N
        self.colors = ["#FF3F3F", "#FF9F3F", "#FFFF3F", "#3FFF3F", "#3F9FFF", "#9F3FFF"] # Brighter colors

        # --- 2. Animation State Variables (The core of Step 4) ---
        self.current_angle_offset = 0.0
        self.rotation_speed = 0.0
        self.base_speed = 10.0
        self.is_spinning = False
        self.frame_delay_ms = 40 # Fast frames (25 FPS)

        # --- 3. GUI Setup ---
        self.mainFrame = Frame(parentWindow, padx=10, pady=10, relief=GROOVE, borderwidth=2, bg="black")
        self.mainFrame.pack(expand=True, fill='both')

        self.mainCanvas = Canvas(self.mainFrame, width=self.canvasSize, height=self.canvasSize, bg="black")
        self.mainCanvas.pack(pady=10)

        # Draw the initial wheel (Calling the method)
        self._draw_wheel(0) 

        # Draw the static pointer
        pointerTipX = self.centerX
        pointerTipY = self.centerY - self.raduis + 5
        pointerWidth = 20
        pointerLenght = 30

        # Adjust base Y to keep the pointer outside the wheel edge
        pointerBaseY = pointerTipY + pointerLenght

        self.mainCanvas.create_polygon(
            pointerTipX, pointerTipY,
            self.centerX - pointerWidth / 2, pointerBaseY, 
            self.centerX + pointerWidth / 2, pointerBaseY,
            fill="white", outline="black", tag="pointer"
        )
        
        self.resultLabel = Label(parentWindow, text="Press SPIN to play!", bg="blue", fg="white", font=('Arial', 14, 'bold'))
        self.resultLabel.pack(pady=20)
        
        self.spinButton = Button(parentWindow, text="Spin", font=('Arial', 16), fg="black", bg="#FFD700", 
                                command=self.start_spin, relief=RAISED, bd=4)
        self.spinButton.pack(pady=5)

    # --- 4. Drawing Logic (Now a separate method) ---
    def _draw_wheel(self, offset_angle):
        
        self.mainCanvas.delete("wheel_parts") 

        for i in range(self.N):
            # Calculate the starting angle based on index, applying the offset
            # 90 degrees offset makes 12 o'clock the starting point
            base_start = 90 + i * self.segmentAngle 
            start_angle_with_offset = base_start + offset_angle
            extent = self.segmentAngle

            x1 = self.centerX - self.raduis
            y1 = self.centerY - self.raduis
            x2 = self.centerX + self.raduis
            y2 = self.centerY + self.raduis

            # Draw Arc
            self.mainCanvas.create_arc(
                x1, y1, x2, y2, start=start_angle_with_offset, 
                extent=extent, fill=self.colors[i % len(self.colors)], 
                style='pieslice', outline="black",
                tags="wheel_parts"
            )
            
            # Calculate Text Position
            # Mid-angle calculation must also include the offset
            midAngle = base_start + (self.segmentAngle / 2) + offset_angle
            midAngleRad = math.radians(midAngle)

            textX = self.centerX + self.textRaduis * math.cos(midAngleRad)
            textY = self.centerY + self.textRaduis * math.sin(midAngleRad)

            # Draw Text
            self.mainCanvas.create_text(
                textX, textY, text=self.masterValues[i], 
                font=('Arial', 10, 'bold'), fill='black',
                tags="wheel_parts", anchor='center', angle=midAngle+90 # Rotate text
            )

    # --- 5. Animation Starter ---
    def start_spin(self):
        if self.is_spinning:
            return
        
        self.is_spinning = True
        # Set speed, adding randomness to make the spin length unpredictable
        self.rotation_speed = self.base_speed + random.uniform(5, 10)
        self.spinButton.config(state=tk.DISABLED)
        self.resultLabel.config(text="Spinning...")
        
        # Start the loop
        self.master.after(self.frame_delay_ms, self.animate_spin)

    # --- 6. Animation Engine ---
    def animate_spin(self):
        
        # 1. Update Angle
        self.current_angle_offset += self.rotation_speed
        self.current_angle_offset %= 360 

        # 2. Redraw Frame
        self._draw_wheel(self.current_angle_offset)

        # 3. Deceleration Logic
        if self.rotation_speed > 0.05: # Deceleration threshold
            self.rotation_speed *= 0.985 # Friction factor
            
            # Continue the loop
            self.master.after(self.frame_delay_ms, self.animate_spin)
        else:
            # 4. STOP Condition
            self.is_spinning = False
            self.rotation_speed = 0.0
            self.spinButton.config(state=tk.NORMAL)
            self.determine_winner()

    # --- 7. Winner Determination ---
    def determine_winner(self):
        # The pointer is located at the center top (90 degrees).
        pointer_angle = 90
        
        # Calculate the wheel's final rotation relative to the pointer (0-360)
        # This angle indicates how far past the 90-degree mark the wheel has rotated.
        # We use 360 - ((current_angle_offset - 90) % 360) for proper clockwise calculation
        
        # Normalize the final angle relative to the 90 degree pointer location:
        # 1. Calculate how far the offset is from 90 (the pointer's location)
        # 2. The winning angle starts at 0 at the top and increases clockwise.
        # We need to map the pointer position (90) back to the 0-360 circle.
        
        # Calculate the total angle rotated relative to the initial 90-degree start
        normalized_rotation = (self.current_angle_offset + 270) % 360 
        
        # Determine the segment index based on the final rotation
        segment_index = int(normalized_rotation // self.segmentAngle)
        
        # Calculate the actual index (which runs backwards on the screen from the top)
        winning_index = (self.N - 1) - (segment_index % self.N)
        
        if 0 <= winning_index < self.N:
            winner = self.masterValues[winning_index]
        else:
            winner = "Error"
        
        self.resultLabel.config(text=f"Winner: {winner}")


if __name__ == "__main__":
    # Load values first
    values = load_values()

    # Create the window
    finalGUI = create_window() 
    
    # Initialize the class and pass the values
    app = RouletteApp(finalGUI, values) 
    
    finalGUI.mainloop()
