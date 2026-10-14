#set up dashboard data unpacking 
from api.apiRequest import get_data
import global_variables as globals
import requests
import time
import os


MasterUrl = globals.Url + "/sendDatatoDashboard"

#placeholder data to send to master,set up the function to extract data and package it into a json format then set json_data = to that function

def receiveDataFromAPI(data):
    response = requests.get(MasterUrl, json=data)
    print(f"Data sent to dashboard: {data}")
    return response

def sendDataLoopToDashboard():

    while True:
        # time.sleep(2) 
        json_data = get_data() 
        try:
            receiveDataFromAPI(json_data)
        except requests.exceptions.RequestException as e:
            print (f"Error receiving data from API: {e}")
