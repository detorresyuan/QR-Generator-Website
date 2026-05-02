class Songs:
   # Represents a song node in the doubly linked list.
   # This is where we find the dummy nodes to prevent overshooting
    def __init__(self, title, artist):
        self.title = title
        self.artist = artist
        self.prev = None
        self.next = None
        
class Playlist:
    #Manages the doubly linked list of Songs.
    #Created a class where the methods of a playlist will come to play
    
    # Initialize where the start and end of the list and set it to None
    # Initialize a pointer to a current song
    def __init__(self):
        self.head = None
        self.tail = None
        self.currentSong = None
       
        #Adds a new song to the end of the playlist.
        # Create a dictionary to store song informations
    def addSong(self, songData: dict) -> None:
        
        title = songData.get("songTitle")
        artist = songData.get("songArtist")
        
        # Create a new Songs object (node)
        new_song = Songs(title, artist)
        
        if self.head is None:
            # Playlist is empty
            self.head = new_song
            self.tail = new_song
            self.currentSong = new_song # Set currentSong to the first song added
        else:
            # Add to the end (tail)
            self.tail.next = new_song # Link previous tail to the new song
            new_song.prev = self.tail # Link new song back to the previous tail
            self.tail = new_song # Update the tail to the new song
            
    def playSong(self):
        #Prints the title and artist of the currently selected song.
        
        if self.currentSong is not None:
            # Access the title and artist attributes of the currentSong object
            songTitle = self.currentSong.title
            songArtist = self.currentSong.artist
            print(f" Now playing '{songTitle}' by '{songArtist}'.")
        else:
            print("Playlist is empty or stopped.")
    
    def nextSong(self):
       #Moves to and plays the next song in the playlist.
        if self.currentSong is not None and self.currentSong.next is not None:
            self.currentSong = self.currentSong.next
            self.playSong() # Call playSong to print the new current song
        elif self.currentSong is not None and self.currentSong.next is None:
             print("Reached the end of the playlist.")
        else:
            print("Playlist is empty.")

    def prevSong(self):
       # Moves to and plays the previous song in the playlist.
        if self.currentSong is not None and self.currentSong.prev is not None:
            self.currentSong = self.currentSong.prev
            self.playSong() # Call playSong to print the new current song
        elif self.currentSong is not None and self.currentSong.prev is None:
             print("Reached the beginning of the playlist.")
        else:
            print("Playlist is empty.")

    def displayPlaylist(self):
        #Prints the full list of songs from head to tail.

        current = self.head
        if current is None:
            print("Playlist empty")
            return # Exit the function if the playlist is empty

        print("--- Full Playlist ---")
        # Loop through the linked list
        while current is not None:
            # Access the title and artist attributes of the song object
            print(f"   - '{current.title}' by '{current.artist}'")
            current = current.next
        print("---------------------")

def main():

    myPlaylist = Playlist()
    
    # Calls and displays the song informations from the addSong dictionary
    myPlaylist.addSong({"songTitle": "Naiilang", "songArtist": "Le John"})
    myPlaylist.addSong({"songTitle": "No. 1 Party Anthem", "songArtist": "Arctic Monkeys"})
    myPlaylist.addSong({"songTitle": "Stairway to Heaven", "songArtist": "Led Zeppelin"})

    # this ensures it starts at the head
    myPlaylist.currentSong = myPlaylist.head 
    print("Starting Playback:")
    # this proves that the songs and play to next and previous like a doubly linked list
    myPlaylist.playSong()  # Naiilang
    
    myPlaylist.nextSong() # No. 1 Party Anthem
    
    myPlaylist.nextSong() # Stairway to Heaven

    myPlaylist.prevSong() # No. 1 Party Anthem
    
    myPlaylist.playSong()  # No. 1 Party Anthem (Explicit call)

    #this displays all of the songs
    print("\nFull Playlist:")
    myPlaylist.displayPlaylist()

#basically outputs and calls everything in the main method
if __name__ == "__main__":
    main()






    #DI KASAMA
    # def addSong(self, index: int) -> int:
    #     cur = self.left.next
    #     while cur and index > 0:
    #         cur = cur.next
    #         index -= 1
    #     if cur and cur != self.right and index == 0:
    #         return cur.val
    #     return -1
    
    

    # def addAtTail(self, val : int) -> None:
    #     node, next, prev = Songs(val), self.right, self.right.prev
    #     prev.next = node
    #     next.prev = node
    #     node.next = next
    #     node.prev = prev 
    
    # def addAtIndex(self, index: int, val: int) -> None:
    #     cur = self.left.next
    #     while cur and index > 0:
    #         cur = cur.next
    #         index -= 1
    #     if cur and index == 0:
    #          node, next, prev = Songs(val), self.right, self.right.prev
    #          prev.next = node
    #          next.prev = node
    #          node.next = next
    #          node.prev = prev 
    
    # def deleteAtIndex(self, index: int) -> None:
    #     cur = self.left.next
    #     while cur and index > 0:
    #         cur = cur.next
    #         index -= 1
    #     if cur and cur != self.right and index == 0:
    #          next, prev = cur.next, cur.prev
    #          next.prev = prev
    #          prev.next = next