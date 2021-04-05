from flask import Blueprint
from flask import json, jsonify, request
import os

api = Blueprint('api', __name__)

from .clouds.make_cloud_mask import process_pipeline
from .model.predict import predict_pipeline


@api.route('/makecloudmask/<foldername>', methods=['GET'])
def run_process(foldername):
    process_pipeline(foldername)
    return "ok"

@api.route('/cloudmasks', methods=['GET'])
def get_cloud_masks():
    return jsonify(os.listdir('./data/aviable_cloud_masks/WGS84'))

@api.route('/cloudmask/<cloudmask>', methods=['GET'])
def get_cloud_mask(cloudmask):
    print(cloudmask)

    with open(f'./data/aviable_cloud_masks/WGS84/{cloudmask}') as f:
         data = json.load(f)
    #data = json.load(f'./data/aviable_cloud_masks/WGS84/{cloudmask}')
    return data

##### model predict

@api.route('/predicts', methods=['GET'])
def get_predicts():
    return jsonify(os.listdir('./data/aviable_predicts/WGS84'))

@api.route('/predict/<predict>', methods=['GET'])
def get_predict(predict):
    print(predict)

    with open(f'./data/aviable_predicts/WGS84/{predict}') as f:
         data = json.load(f)
    return data

@api.route('/makepredict', methods=['GET'])
def make_predict():
    from os.path import exists, join
    oldImg = request.args.get('oldImg', None)  # use default value repalce 'None'
    newImg = request.args.get('newImg', None)
    if (not oldImg) or (not newImg):
        return jsonify({'Error': 'No image selected'})

    oldPath = join('./data/aviable_images', oldImg)
    newPath = join('./data/aviable_images', newImg)

    if not exists(oldPath) or not exists(newPath):
        return jsonify({'Error': 'Some folder not exists'})

    predict_pipeline(oldImg, newImg)

    # return jsonify({'firstImg': firstImg, 'secondImg': secondImg})
    return "ok"
