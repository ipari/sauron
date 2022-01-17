import os
from flask import Flask


def create_app():
    app = Flask(__name__)

    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    return app
