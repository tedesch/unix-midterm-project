import global_variables as globals
from utilities import setMode
from api import apiDef


print ("Welcome to the Unix Midterm Project\n Current mode is: " + globals.mode)
globals.mode = setMode.changeModeQuestion()

if globals.mode == "master":
    app = apiDef.create_app()
    if __name__ == '__main__':
        app.run(debug=True)

#else :
#set up a loop function that will send data to app
