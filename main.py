import os

import logging

from flask import Flask
from flask import jsonify
from flask import request
from flask import make_response
from processing import api as api_blueprint

app = Flask(__name__)
#app.debug = True

app.register_blueprint(api_blueprint)

# logging.basicConfig(filename='record.log', level=logging.DEBUG,
#                     format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

@app.route('/')
def hello():
    return "Hello World!"


@app.route('/images')
def get_images():
    import os
    return jsonify(os.listdir('./data/aviable_images'))

# @app.route('/makecloudsmask/<foldername>', methods=['GET'])
# def run_mask(foldername):
#     fldImages = os.path.normpath('./data/aviable_images')
#     fldImage = os.path.join(fldImages, foldername)
#     if not os.path.exists(fldImage):
#         return make_response(jsonify({'Error': 'Folder not exists'}), 500)
#
#     #return make_response(jsonify({'folder': f'{fldImage}'}), 200)
#     #process_pipeline(fldImage)



if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, passthrough_errors=True)
