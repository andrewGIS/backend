from flask import Blueprint, jsonify

api = Blueprint('general', __name__)


@api.route('/')
def hello():
    return "Hello World!"


@api.route('/images')
def get_images():
    import os
    return jsonify({'images': os.listdir('./data/aviable_images')})
