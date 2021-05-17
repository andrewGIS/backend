import os

class BaseConfig():
    API_PREFIX = '/api'
    TESTING = False
    DEBUG = False

class ProductionConfig(BaseConfig):
    FLASK_ENV = 'production'
    IMG_FLD = os.path.normpath('./data/aviable_images')
    DEBUG = False
    TESTING = False
    PASSTHROUGH_ERRORS = True
    CELERY_BROKER = 'Test'


class devConfig(BaseConfig):
    IMG_FLD = os.path.normpath('./data/aviable_images')
    TEMP_PARTS_FLD = os.path.normpath("./processing/temp/img_parts")
    FLASK_ENV = 'development'
    DEBUG = True
    CELERY_BROKER = 'Test'
    USE_RELOADER = True


class TestingConfig(BaseConfig):
    TESTING = os.path.normpath('./data/aviable_images')
    DEBUG = True
    USE_RELOADER = True
    CELERY_BROKER = 'Test'
