from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register the API blueprint
    from v1.api import api_blueprint
    app.register_blueprint(api_blueprint, url_prefix="/api/v1")

    # Register error handlers (optional)
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    return app
