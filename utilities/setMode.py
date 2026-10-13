

def askForMode ():
    mode = input("Enter slave or master: ")
    if mode != "slave" and mode != "master":
        print ("please type either slave or master")
        return askForMode()  
    elif mode == "slave":
        print ("Mode set to slave")
        return "slave"
    elif mode == "master":
        print ("Mode set to master")
        return "master"
    

def changeModeQuestion():    
    print ("Would you like to change the mode? (y/n)")
    changeMode = input()
    if changeMode != "y" and changeMode != "n":
            print ("please type either y or n")
            return changeModeQuestion()
    if changeMode == "y":
        return askForMode()
         
    
    