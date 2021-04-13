from flask import Blueprint, jsonify, request, send_from_directory
from processing.utils import get_subset_from_image
from flask import send_file
import os

TEMP_PARTS_FLD = os.path.normpath("./processing/temp/img_parts")

api = Blueprint('general', __name__)


@api.route('/')
def hello():
    return "Hello World!"


@api.route('/images')
def get_images():
    import os
    return jsonify({'images': os.listdir('./data/aviable_images')})


@api.route('/get_image_part', methods=['GET'])
def make_predict():
    imgFld = request.args.get('imgFld', None)  # use default value repalce 'None'
    channel = request.args.get('channel', None)  # use default value repalce 'None'
    xmax = request.args.get('xmax', None)
    xmin = request.args.get('xmin', None)
    ymax = request.args.get('ymax', None)
    ymin = request.args.get('ymin', None)
    if not imgFld:
        return jsonify({'Error': 'No image selected'})

    if (not xmax) or (not xmin) or (not ymax) or (not ymin):
        return jsonify({'Error': 'Not all coordinates specified'})

    xmin, xmax, ymin, ymax = float(xmin), float(xmax), float(ymin), float(ymax)
    out_file = get_subset_from_image(imgFld, channel, xmin, xmax, ymin, ymax)
    return send_file(out_file, mimetype='image/bmp')
