import os
from flask import jsonify
import json
from flask import Blueprint, current_app

from processing.clouds.make_cloud_mask import process_pipeline

api = Blueprint('cloud', __name__)


@api.route('/makecloudmask/<foldername>', methods=['GET'])
def run_process(foldername):
    #print(current_app.config)
    process_pipeline(foldername)
    return "ok"


@api.route('/cloudmasks', methods=['GET'])
def get_cloud_masks():
    return jsonify({"masks": os.listdir('./data/aviable_cloud_masks/WGS84')})


@api.route('/cloudmask/<cloudmask>', methods=['GET'])
def get_cloud_mask(cloudmask):
    print(cloudmask)

    with open(f'./data/aviable_cloud_masks/WGS84/{cloudmask}') as f:
        data = json.load(f)
    return data
