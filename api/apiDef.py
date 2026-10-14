import flask
import global_variables as globals
from queue import Queue

def create_app():
    mode = globals.mode
    app = flask.Flask(__name__)
    maxsizeQueue = 20
    packetQueues = Queue(maxsize=maxsizeQueue)  

    
    @app.route('/')
    def index():
        return flask.jsonify({"message": "Welcome to the Unix Midterm Project"})

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
    
