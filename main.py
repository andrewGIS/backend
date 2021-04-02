import os

import logging

from flask import Flask
from flask import jsonify
from flask import request
from flask import make_response



app = Flask(__name__)
#app.debug = True

logging.basicConfig(filename='record.log', level=logging.DEBUG,
                    format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

from processing.clouds.make_cloud_mask import process_pipeline

@app.route('/')
def hello():
    return "Hello World!"


@app.route('/images')
def get_images():
    import os
    return jsonify(os.listdir('./data/aviable_images'))

@app.route('/makecloudsmask/<foldername>', methods=['GET'])
def run_mask(foldername):
    fldName = request.args.get('foldername')
    fldImages = os.path.normpath('./data/aviable_images')
    fldImage = os.path.join(fldImages, foldername)
    if not os.path.exists(fldImage):
        return make_response(jsonify({'Error': 'Folder not exists'}), 500)

    #return make_response(jsonify({'folder': f'{fldImage}'}), 200)
    process_pipeline(fldImage)



if __name__ == '__main__':
    app.run(debug=True)
