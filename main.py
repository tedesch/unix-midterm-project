import global_variables as globals
from utilities import setMode
from api import apiDef as apdef
from api import apiRequest as req

print ("Welcome to the Unix Midterm Project\n Current mode is: " + globals.mode)
globals.mode = setMode.changeModeQuestion()
 #not finished yet, add the ability for master to look at it's own data

if globals.mode == "master":
    app = apdef.create_app()
    if __name__ == '__main__':
        app.run(debug=True, use_reloader=False)
 #not finished yet, add the json data extraction and packaging function there is a placeholder get_data function
else :
    while True:
        req.sendDataLoop()
    #not finished yet    

