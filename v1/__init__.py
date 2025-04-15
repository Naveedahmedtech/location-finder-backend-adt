from flask import Flask
from config import Config
from v1.homepage_routes import homepage_bp
from v1.about_info_routes import about_bp
from v1.privacy_policy_routes import privacy_bp
from v1.auth_routes import auth_blueprint
from v1.api import api_blueprint, distance_blueprint
from v1.geonames_routes import geo_blueprint

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    
    # Register the API blueprint
    app.register_blueprint(api_blueprint, url_prefix="/api/v1")
    app.register_blueprint(homepage_bp, url_prefix="/api/v1")
    app.register_blueprint(about_bp, url_prefix="/api/v1/about")
    app.register_blueprint(privacy_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_blueprint, url_prefix="/api/v1/auth")
    app.register_blueprint(geo_blueprint, url_prefix="/api/v1/geo")
    app.register_blueprint(distance_blueprint, url_prefix="/api/v1/distances")

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    return app
