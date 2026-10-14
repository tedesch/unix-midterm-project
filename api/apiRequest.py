import global_variables as globals
import requests
import time
import asyncio
from utilities.dataExtraction import get_json_data
MasterUrl = globals.Url + "/recivedata"

#placeholder data to send to master,set up the function to extract data and package it into a json format then set json_data = to that function
def get_data():
    return asyncio.run(get_json_data())

def send_data_to_master(data):
    response = requests.post(MasterUrl, json=data)
    return response

def sendDataLoop():
    while True:
        json_data = get_data() # change once the function is set up to extract data and package it into a json format
        try:
            send_data_to_master(json_data)
        except requests.exceptions.RequestException as e:
            print (f"Error sending data to master: {e}")