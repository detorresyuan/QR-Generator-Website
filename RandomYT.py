from tkinter import *                     # import all names from the tkinter GUI library
from tkinter import messagebox            # import messagebox for dialog windows
import random                             # import random for choosing random items
from PIL import Image, ImageTk            # import PIL to open/resize images and convert to Tk images
from googleapiclient.discovery import build  # import build to create the YouTube API client
import requests                           # import requests to download thumbnail images
import io                                 # import io to handle in-memory byte streams for images
import os                                 # import os to access environment variables and filesystem info
import sys                                # import sys to exit the program on fatal errors

def mainWindow():                         # define function to create the main application window
    window = Tk()                         # create the main Tkinter window object
    window.title("Random Youtube Video Fetcher")  # set the window title shown on the title bar
    window.geometry("1500x900")           # set the initial window size (width x height)
    try:
        icon = PhotoImage(file = "niga.png")  # try to load a .png file to use as window icon
        window.iconphoto(True, icon)      # set the loaded image as the window icon
    except Exception:
        # ignore missing or invalid icon files and continue without crashing
        pass
    return window                         # return the created window object to the caller

def main():                               # main entry function to launch the GUI application
    finalGUI = mainWindow()               # create the main window by calling mainWindow()
    app = RandomYoutubeApp(finalGUI)      # create an instance of the app class and attach it to the window
    finalGUI.mainloop()                   # start Tkinter's event loop to respond to GUI events

class RandomYoutubeApp:                   # define the application class that manages the interface and logic
    def __init__(self, parentwindow):     # constructor runs when creating an instance of the class
        self.master = parentwindow        # store a reference to the Tkinter parent window
        # prefer environment variable, fallback to any hardcoded key if present
        self.apiKey = os.getenv("YOUTUBE_API_KEY") or "AIzaSyAKBoXfwhSJh1YJuP2l2HuHAOwU04hBwjA" # get the API key from the environment variable
        if not self.apiKey:               # if the environment variable is not set
            messagebox.showerror("Configuration Error", 
                                "API Key not found. Please set the 'YOUTUBE_API_KEY' environment variable.")  # notify user
            sys.exit()                     # exit the program because the API key is required

        self.YTApiServiceName = "youtube"  # name of the Google API service (YouTube)
        self.YTAPiVer = "v3"              # YouTube Data API version
        self.maxSearchResults = 50        # maximum number of search results to request

        try:
            # build the YouTube API client using the provided API key
            self.youtube = build(self.YTApiServiceName, self.YTAPiVer, developerKey = self.apiKey)
        except Exception as e:
            # if building the client fails, show an error and exit
            messagebox.showerror("Youtube Init Error", f"Error initializing Youtube Service: {e}")
            sys.exit()

        # storage for videos (dicts from API) and current index
        self.YTlist = []                   # list to store video result objects for navigation
        self.currentIndex = -1             # index of the currently displayed video; -1 means none yet

        # canvas sizes
        self.canvasH = 620                 # canvas (display area) height in pixels
        self.canvasW = 900                # canvas width in pixels
        # create a Canvas widget to display thumbnails and text
        self.mainCanvas = Canvas(parentwindow, height = self.canvasH, width = self.canvasW,
                            borderwidth = 2, bg = "#414141")
        self.mainCanvas.pack(pady = 30, padx = 20)  # pack the canvas into the window with padding

        # buttons and search
        self.getButton = Button(parentwindow, relief = RAISED, width = 10, bg = "#DBDBDB",
                                text = "GET", fg = "#1F1F1F", command = self.handlerOne)  # button to perform search + pick
        self.getButton.place(y = 657, x = 650)  # place the GET button at absolute coordinates
        self.nextButton = Button(parentwindow, relief = RAISED, width = 10, bg = "#DBDBDB",
                                text = "->", fg = "#1F1F1F", command = self.nextFunction)  # button to show next video
        self.nextButton.place(y = 657, x = 735)  # position the next button
        self.prevButton = Button(parentwindow, relief = RAISED, width = 10, bg = "#DBDBDB",
                                text = "<-", fg = "#1F1F1F", command = self.prevFunction)  # button to show previous video
        self.prevButton.place(y = 657, x = 565)  # position the previous button
        self.searchBar = Entry(parentwindow, width = 40, bg = "#FFFFFF", fg = "#000000",
                               borderwidth = 2)  # entry widget where the user types the search query
        self.searchBar.insert(0, "Enter a Topic")  # insert placeholder text into the search bar
        self.searchBar.place(y = 10, x = 572)  # place the search bar in the window

        # keep reference to PhotoImage to prevent GC
        self._photo_image = None             # store the currently displayed PhotoImage to prevent it being garbage-collected

    def searchQuery(self):                  # perform a YouTube search using the text from the search bar
        self.userInputSearch = self.searchBar.get().strip()  # read and strip whitespace from the entry widget
        try:
            if not self.userInputSearch:    # if the search text is empty after stripping
                return None                 # return None to indicate no search performed
            # call the YouTube API to perform a search with the user's query
            self.searchResponse = self.youtube.search().list(
                q = self.userInputSearch,
                part = "id,snippet",
                type = "video",
                maxResults = self.maxSearchResults
            ).execute()                    # execute the API request and store the response
            return self.searchResponse     # return the response object to the caller
        except Exception as e:
            # show an error dialog when search fails and return None
            messagebox.showerror("Youtube Search Error", f"Failure in fetching Youtube Data: {e}")
            return None

    def pickRandomFromResults(self, searchResults):  # choose a random video item from the search response
        if searchResults is None or "items" not in searchResults:  # validate the response structure
            messagebox.showinfo("No results")  # notify user if nothing was returned
            return None
        items = searchResults.get("items", [])  # get the list of result items safely
        # filter the items to only include actual videos (not channels or playlists)
        videos = [item for item in items if item.get("id", {}).get("kind") == "youtube#video"]
        if not videos:                       # if no video items were found
            messagebox.showinfo("No Videos Found")  # inform the user
            return None
        return random.choice(videos)         # return a randomly chosen video dict

    def download_and_prepare_image(self, url):  # download a thumbnail URL and convert it to a Tk image
        try:
            resp = requests.get(url, timeout=10)  # fetch the image bytes with a timeout
            resp.raise_for_status()             # raise an error for non-200 responses
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")  # open image from bytes and ensure RGBA mode
            img = img.resize((self.canvasW, self.canvasH), Image.LANCZOS)  # resize the image to fit the canvas
            return ImageTk.PhotoImage(img)      # convert the PIL image to a PhotoImage usable by Tkinter
        except Exception:
            return None                         # on any error return None so caller can handle it

    def displayVideo(self, index):            # display the video at the given index from self.YTlist
        if index < 0 or index >= len(self.YTlist):  # validate the index
            return                             # do nothing if the index is out of range
        video = self.YTlist[index]             # get the video dict at the index
        title = video["snippet"]["title"]      # extract the video's title string
        # attempt to get the high-resolution thumbnail URL, fallback to default if not available
        thumbnail_url = video["snippet"]["thumbnails"].get("high", {}).get("url") or \
                        video["snippet"]["thumbnails"].get("default", {}).get("url")
        # video id is usually under id.videoId for search results
        video_id = video["id"].get("videoId") or video["id"].get("channelId") or ""

        # clear canvas of previous drawings/images
        self.mainCanvas.delete("all")

        # download and show thumbnail if available
        img = None
        if thumbnail_url:
            img = self.download_and_prepare_image(thumbnail_url)  # try to download and prepare thumbnail
        if img:
            self._photo_image = img              # keep a reference to prevent garbage collection
            # draw the image centered on the canvas
            self.mainCanvas.create_image(self.canvasW//2, self.canvasH//2, image=self._photo_image, anchor=CENTER)
        else:
            # if no thumbnail, draw a plain rectangle as a visual placeholder
            self.mainCanvas.create_rectangle(0, 0, self.canvasW, self.canvasH, fill="#222222")

        # draw the title centered near the bottom of the canvas
        self.mainCanvas.create_text(self.canvasW//2, self.canvasH - 30, text=title, fill="white", font=("Arial", 18), width=self.canvasW-20)
        # draw the video id in the top-left corner for reference
        self.mainCanvas.create_text(10, 10, text=f"Video ID: {video_id}", fill="white", anchor="nw", font=("Arial", 10))

    def handlerOne(self):                     # called when the GET button is pressed
        searchResults = self.searchQuery()    # perform a search and get results
        if searchResults is None:             # if no results were returned or search canceled
            return                            # do nothing
        picked = self.pickRandomFromResults(searchResults)  # choose a random video item
        if picked is None:                    # if picking failed for some reason
            return                            # do nothing
        # reset list and add first picked
        self.YTlist = [picked]                # store the single picked video as the current list
        self.currentIndex = 0                 # set the current index to 0 (first item)
        self.displayVideo(self.currentIndex)  # display the picked video on the canvas

    def nextFunction(self):                   # show the next video (or fetch another random one)
        if not self.YTlist:                   # if there are no videos stored yet
            messagebox.showinfo("Error", "Please GET first")  # instruct the user to perform a GET first
            return
        # If there are more cached videos, go next; otherwise pick a new random and append
        if self.currentIndex < len(self.YTlist) - 1:
            self.currentIndex += 1            # move the index forward if cached next exists
        else:
            # try to pick another from the last search results if available
            try:
                last_search = getattr(self, "searchResponse", None)  # get last search response if present
                picked = self.pickRandomFromResults(last_search)     # pick another random video
                if picked:
                    self.YTlist.append(picked)      # append the newly picked video to the list
                    self.currentIndex = len(self.YTlist) - 1  # move index to the new last item
            except Exception:
                pass                                # ignore errors here and continue
        self.displayVideo(self.currentIndex)     # display the current index's video

    def prevFunction(self):                     # show the previous video in the stored list
        if not self.YTlist:                     # if no videos are stored yet
            messagebox.showinfo("Error", "Please GET first")  # instruct the user to perform a GET first
            return
        # wrap-around to the end when moving before the first item
        self.currentIndex = (self.currentIndex - 1) % len(self.YTlist)  # decrement index with wrap-around
        self.displayVideo(self.currentIndex)     # display the video at the new index

if __name__ == "__main__":                     # if this file is run as the main program (not imported)
    main()                                     # call main() to start the application