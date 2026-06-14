import os

from flask import Flask, render_template

from config import Config
from models import db
from routes import api


def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    db.init_app(app)
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return render_template("index.html")

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    create_app().run(debug=True, threaded=True)
