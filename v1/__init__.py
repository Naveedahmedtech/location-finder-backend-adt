from flask import Flask
from config import Config
from v1.homepage_routes import homepage_bp
from v1.about_info_routes import about_bp
from v1.privacy_policy_routes import privacy_bp
def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    
    # Register the API blueprint
    from v1.homepage_routes import api_blueprint
    app.register_blueprint(api_blueprint, url_prefix="/api/v1")
    app.register_blueprint(homepage_bp, url_prefix="/api/homepage")
    app.register_blueprint(about_bp, url_prefix="/api/about")
    app.register_blueprint(privacy_bp, url_prefix="/api/pp")

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    return app
