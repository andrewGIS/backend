import logging
import os
import config

from flask import Flask
from flask_cors import CORS

from api.clouds import api as cloud_api
from api.predict import api as predict_api
from api.general import api as general_api

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s]: {} %(levelname)s %(message)s'.format(os.getpid()),
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[logging.StreamHandler()])

logger = logging.getLogger()

def create_app():

    logger.info(f'Starting app in {config.APP_ENV} environment')

    app = Flask(__name__)
    CORS(app, resources={
        r"/*": {
            "origins": "*"
        }
    })

    app.config.from_object('config')

    app.register_blueprint(cloud_api)
    app.register_blueprint(predict_api)
    app.register_blueprint(general_api)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
