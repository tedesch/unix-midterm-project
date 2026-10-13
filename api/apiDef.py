import flask
import global_variables as globals
def create_app():
    mode = globals.mode
    app = flask.Flask(__name__)  
    @app.route('/')
    def index():
        return flask.jsonify({"message": "this is a test"})

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
    def receive_data():
        data = flask.request.get_json()
        # Process the received data
        app.config['received_data'] = data  # Store the received data in the app's config
        return flask.jsonify({"success": True, "received_data": data}), 200
    @app.route("/sendDatatoDashboard", methods=["GET"])
    def send_data_to_dashboard():
        data = app.config.get('received_data')
        if data is None:
            return flask.jsonify({"error": "No data received yet"}), 404      
        return flask.jsonify(data), 200    


    return app
    

