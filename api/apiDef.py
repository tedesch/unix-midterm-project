import json
import hmac
import flask
import global_variables as globals
from queue import Queue
from threading import Lock
from time import time
from pathlib import Path
from uuid import uuid4

def create_app():
    mode = globals.mode
    gui_directory = Path(__file__).resolve().parent.parent / "gui"
    app = flask.Flask(
        __name__,
        template_folder=gui_directory / "templates",
        static_folder=gui_directory / "static",
    )
    maxsizeQueue = 150
    packetQueues = Queue(maxsize=maxsizeQueue)  
    latestPackets = {}
    stressCommands = {}
    stressStatuses = {}
    packetLock = Lock()

    def record_telemetry(packet):
        with packetLock:
            latestPackets[packet["name"]] = (time(), packet)

    def command_authorized():
        return bool(globals.command_token) and hmac.compare_digest(
            flask.request.headers.get("Authorization", ""),
            f"Bearer {globals.command_token}",
        )

    app.extensions["record_telemetry"] = record_telemetry

    
    @app.route('/')
    def index():
        return flask.render_template("dashboard.html")

    @app.route("/api/vms", methods=["GET"])
    def get_vms():
        with packetLock:
            vms = [
                {
                    "name": name,
                    "updated_at": updated_at,
                    "metrics": metrics,
                    "stress": stressStatuses.get(name),
                }
                for name, (updated_at, metrics) in latestPackets.items()
            ]
        return flask.jsonify({"vms": vms})

    @app.route("/api/vms/<path:vm_name>/stress", methods=["POST"])
    def start_workload(vm_name):
        if not command_authorized():
            return flask.jsonify({"error": "Valid command token required"}), 401

        with packetLock:
            vm = latestPackets.get(vm_name)
            if vm is None or time() - vm[0] > 30:
                return flask.jsonify({"error": "VM is not currently online"}), 404
            if vm[1].get("is_host"):
                return flask.jsonify({"error": "Host workload triggers are not supported"}), 400
            current_status = stressStatuses.get(vm_name, {})
            if current_status.get("status") in ("queued", "running"):
                return flask.jsonify({"error": "A workload is already active for this VM"}), 409

            command_id = str(uuid4())
            stressCommands[vm_name] = {"id": command_id, "type": "start_workload"}
            stressStatuses[vm_name] = {
                "id": command_id,
                "status": "queued",
                "message": "Workload queued",
            }

        return flask.jsonify({"id": command_id, "status": "queued"}), 202

    @app.route("/api/commands/<path:vm_name>", methods=["GET"])
    def get_vm_command(vm_name):
        if not command_authorized():
            return flask.jsonify({"error": "Valid command token required"}), 401

        with packetLock:
            command = stressCommands.pop(vm_name, None)
            if command is not None:
                stressStatuses[vm_name] = {
                    "id": command["id"],
                    "status": "running",
                    "message": "Starting workload",
                }

        return flask.jsonify({"command": command})

    @app.route(
        "/api/commands/<path:vm_name>/<command_id>/result",
        methods=["POST"],
    )
    def report_command_result(vm_name, command_id):
        if not command_authorized():
            return flask.jsonify({"error": "Valid command token required"}), 401

        result = flask.request.get_json()
        if not isinstance(result, dict) or not isinstance(result.get("success"), bool):
            return flask.jsonify({"error": "Result must include a boolean success value"}), 400

        with packetLock:
            status = stressStatuses.get(vm_name)
            if status is None or status.get("id") != command_id:
                return flask.jsonify({"error": "Unknown workload command"}), 404
            status["status"] = "completed" if result["success"] else "failed"
            status["message"] = (
                "Workload started"
                if result["success"]
                else str(result.get("error", "Workload failed"))[:500]
            )

        return flask.jsonify({"status": status["status"]})

    @app.route('/sayMode', methods=['GET'])
    def get_mode(): 
        return flask.jsonify({"message": mode})

    @app.route("/setMode", methods=["POST"])
    def set_mode():
        data = flask.request.get_json()
        mode = data.get("mode")

        if mode not in ("slave", "master"):
            return flask.jsonify({
                "error": "Mode must be slave or master"
            }), 400

        return flask.jsonify({
            "mode": mode,
            "is_slave": mode == "slave"
        })
    @app.route("/recivedata", methods=["POST"])
    def sendData():
        jsonData = flask.request.get_json()
        if jsonData is None:
            return flask.jsonify({"error": "No data received"}), 400
        if isinstance(jsonData, str):
            try:
                jsonData = json.loads(jsonData)
            except json.JSONDecodeError:
                return flask.jsonify({"error": "Packet must contain valid JSON"}), 400
        if not isinstance(jsonData, dict):
            return flask.jsonify({"error": "Packet must be a JSON object"}), 400
        name = jsonData.get("name")
        if not isinstance(name, str) or not name.strip():
            return flask.jsonify({"error": "Packet must include a VM name"}), 400

        record_telemetry(jsonData)

        if packetQueues.full():
            for _ in range(maxsizeQueue // 2):
                packetQueues.get()  # Remove the oldest data to make space for new data

        packetQueues.put(jsonData)
        
        return flask.jsonify({"message": "Data received successfully"}), 200
    #################
    #make it goood 
    #################
    @app.route("/printQueue", methods=["GET"])
    def printQueue():
        while True:
            queue_contents = list(packetQueues.queue)
            return flask.jsonify({"queue_contents": queue_contents}), 200
    @app.route("/sendDatatoDashboard", methods=["GET"])
    def send_data_to_dashboard():
        data = packetQueues.get() if not packetQueues.empty() else None
        if data is None:
            return flask.jsonify({"error": "No data received yet"}), 404      
        return flask.jsonify(data), 200    


    return app
    
