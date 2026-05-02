import random # a randomizer function

with open("movies.txt", "r") as f: # opens a file inside a folder to use and reads it as "f" or file
    rawLine = f.readlines() # a unedited file called rawLine for it still has whitelines and /n's
                            # reads the lines into a list
    movieList = [] # created a master list or an array for the movies

    for movieLine in rawLine: # cleans the movie lines and returns it into the master list
        cleanTitle = movieLine.strip()
        
        movieList.append(cleanTitle)
    
    pickedMovie = random.choice(movieList) # a random choice picker function

def main():
    print(pickedMovie) # outputs the chosen movie

main() # does not need to be in a print statement



        




