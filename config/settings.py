import os
class BaseConfig():
    TESTING = False
    DEBUG = False


class DevConfig(BaseConfig):
    FLASK_ENV = 'development'
    DEBUG = True
    # flds
    IMG_FLD = os.path.normpath('./data/aviable_images')
    STATIC_FLD = os.path.normpath("./static")

    TEMP_PARTS_FLD = os.path.normpath('./processing/temp/img_parts')
    TEMP_FLD = os.path.normpath("./processing/temp")
    TEMP_WARP_FLD = os.path.normpath("./processing/temp/warp")
    TEMP_STACK_FLD = os.path.normpath("./processing/temp/stack")
    TEMP_TILES_FLD = os.path.normpath("./processing/temp/tiles")
    TEMP_PREDICT_FLD = os.path.normpath("./processing/temp/predicts")

    OUT_CLOUD_FLD_WGS = os.path.normpath('./data/aviable_cloud_masks/WGS84')
    OUT_CLOUD_FLD = os.path.normpath('./data/aviable_cloud_masks/project')

    OUT_PREDICT_FLD = os.path.normpath('./data/aviable_predicts/project')
    OUT_PREDICT_FLD_WGS = os.path.normpath('./data/aviable_predicts/WGS84')
    OUT_PREDICT_FLD_FILTERED = os.path.normpath('./data/aviable_predicts/filtered')

    # redis for celery
    CELERY_BROKER = 'pyamqp://rabbit_user:rabbit_password@broker-rabbitmq//'

class ProductionConfig(BaseConfig):
    FLASK_ENV = 'production'
    SQLALCHEMY_DATABASE_URI = 'postgresql://db_user:db_password@db-postgres:5432/flask-deploy'
    CELERY_BROKER = 'pyamqp://rabbit_user:rabbit_password@broker-rabbitmq//'
    CELERY_RESULT_BACKEND = 'rpc://rabbit_user:rabbit_password@broker-rabbitmq//'


class TestConfig(BaseConfig):
    FLASK_ENV = 'development'
    TESTING = True
    DEBUG = True
    # make celery execute tasks synchronously in the same process
    CELERY_ALWAYS_EAGER = True