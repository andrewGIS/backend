import time

from flask import Flask
from flask_cors import CORS
from flask import jsonify
from flask_socketio import SocketIO, send, emit
from celery import Celery

from controllers.clouds import api as cloud_api
from controllers.predict import api as predict_api
from controllers.general import api as general_api

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*"
    }
})
socketio = SocketIO(app)

celery = Celery(app.name)
celery.conf.update(app.config)

# app.debug = True

app.register_blueprint(cloud_api)
app.register_blueprint(predict_api)
app.register_blueprint(general_api)


# logging.basicConfig(filename='record.log', level=logging.DEBUG,
#                     format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')




# @app.route('/makecloudsmask/<foldername>', methods=['GET'])
# def run_mask(foldername):
#     fldImages = os.path.normpath('./data/aviable_images')
#     fldImage = os.path.join(fldImages, foldername)
#     if not os.path.exists(fldImage):
#         return make_response(jsonify({'Error': 'Folder not exists'}), 500)
#
#     #return make_response(jsonify({'folder': f'{fldImage}'}), 200)
#     #process_pipeline(fldImage)

@app.route('/runtest')
def test_socket():
    socketio.emit('update status', "Reosolution check")
    time.sleep(10)
    socketio.emit('update status', "Reosolution1 check")
    time.sleep(10)
    socketio.emit('update status', "Reosolution2 check")
    time.sleep(10)


@socketio.on('update status')
def handle_my_custom_event(message):
    socketio.send(message)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, passthrough_errors=True)
    #socketio.run(app, debug=True, use_reloader=True, passthrough_errors=True)
