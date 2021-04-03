from flask import Blueprint

api = Blueprint('api', __name__)

from .clouds.make_cloud_mask import process_pipeline


@api.route('/makecloudmask/<foldername>')
def run_process(foldername):
    process_pipeline(foldername)
    return "ok"
