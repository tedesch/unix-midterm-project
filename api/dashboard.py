#set up dashboard data unpacking 
import global_variables as globals
import requests
import time
import os


MasterUrl = globals.Url + "/sendDatatoDashboard"

#placeholder data to send to master,set up the function to extract data and package it into a json format then set json_data = to that function
def get_data():
    return {"data": "506"}

def receiveDataFromMaster(data):
    response = requests.get(MasterUrl, json=data)
    return response

def sendDataLoop():

    ##refactor this shiet
    """
    while True:
        time.sleep(2) 
        json_data = get_data() # change once the function is set up to extract data and package it into a json format
        try:
            receiveDataFromMaster(json_data)
        except requests.exceptions.RequestException as e:
            print (f"Error receiving data from master: {e}")

    """