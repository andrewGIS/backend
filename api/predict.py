from flask import Blueprint
from flask import json, jsonify, request
import os
from tasks import celery

from processing.model.predict import predict_pipeline

api = Blueprint('predict', __name__)


@api.route('/predicts', methods=['GET'])
def get_predicts():
    return jsonify({"predicts": os.listdir('./data/aviable_predicts/WGS84')})


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

    #task = predict_pipeline(oldImg, newImg).delay()
    predict_pipeline(oldImg, newImg)

    #return jsonify({'firstImg': firstImg, 'secondImg': secondImg})
    return jsonify('ok')
    #return jsonify({'task_id': task.id})


@api.route('/predict_status', methods=['GET'])
def predict_status():
    task_id = request.args.get('task_id', None)
    if not task_id:
        return jsonify({'Error': 'Task id is not set'})
    task = celery.AsyncResult(task_id)
    return jsonify(task.result)
