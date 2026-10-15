import global_variables as globals
import requests
import time
import asyncio
import subprocess
from urllib.parse import quote
from utilities.dataExtraction import get_json_data

#placeholder data to send to master,set up the function to extract data and package it into a json format then set json_data = to that function
def get_data():
    return asyncio.run(get_json_data())

def send_data_to_master(data):
    response = requests.post(f"{globals.Url.rstrip('/')}/recivedata", json=data)
    return response

def report_workload_result(command_id, result):
    url = (
        f"{globals.Url.rstrip('/')}/api/commands/"
        f"{quote(globals.name, safe='')}/{command_id}/result"
    )
    response = requests.post(
        url,
        json=result,
        headers={"Authorization": f"Bearer {globals.command_token}"},
        timeout=5,
    )
    response.raise_for_status()

def poll_workload_command():
    if not globals.command_token:
        return

    url = f"{globals.Url.rstrip('/')}/api/commands/{quote(globals.name, safe='')}"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {globals.command_token}"},
        timeout=5,
    )
    response.raise_for_status()
    command = response.json().get("command")
    if command is None:
        return
    if command.get("type") != "start_workload":
        raise ValueError(f"Unsupported workload command: {command.get('type')}")

    command_id = command["id"]
    try:
        subprocess.run(
            ["sudo", "-n", "systemctl", "start", "workload-simulator.service"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as error:
        details = (error.stderr or error.stdout or "").strip()
        message = f"systemctl exited with status {error.returncode}"
        if details:
            message = f"{message}: {details}"
        result = {"success": False, "error": message}
    except (OSError, subprocess.SubprocessError) as error:
        result = {"success": False, "error": str(error)}
    else:
        result = {"success": True}

    report_workload_result(command_id, result)

def sendDataLoop():
    next_command_poll = 0.0
    while True:
        json_data = get_data() # change once the function is set up to extract data and package it into a json format
        try:
            send_data_to_master(json_data)
        except requests.exceptions.RequestException as e:
            print (f"Error sending data to master: {e}")
        if time.monotonic() >= next_command_poll:
            try:
                poll_workload_command()
            except (requests.exceptions.RequestException, ValueError) as e:
                print(f"Error checking or running workload command: {e}")
            next_command_poll = time.monotonic() + 1