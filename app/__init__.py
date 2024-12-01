from flask import Flask
from app.api.compare import compare_bp

def create_app():
    app = Flask(__name__)

    # Register Blueprint for the  routes
    app.register_blueprint(compare_bp, url_prefix='/api')

    return app
