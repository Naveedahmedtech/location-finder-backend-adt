import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, jsonify, Blueprint
from db import user_collection
from config import Config


auth_blueprint = Blueprint("api_auth", __name__)
# Create Login API
@auth_blueprint.route("/login", methods=["POST"])
def login():
    """
    POST /api/v1/login
    Expects:
    {
      "username": "user1",
      "password": "password"
    }
    Returns JWT token if login is successful.
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # Validate username and password
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Check if user exists using find_one instead of get
    user = user_collection.find_one({"username": username})
    if user and check_password_hash(user["password"], password):  # You should hash passwords in the real app
        # Create JWT token with expiry time of 1 hour
        token = jwt.encode({
            "username": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, Config.SECRET_KEY, algorithm="HS256")
        
        return jsonify({"token": token}), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

@auth_blueprint.route("/signup", methods=["POST"])
def signup():
    """
    POST /api/v1/signup
    Expects:
    {
      "username": "new_user",
      "password": "securepassword"
    }
    Creates a new user if the username is not already taken.
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Check if username already exists
    existing_user = user_collection.find_one({"username": username})
    if existing_user:
        return jsonify({"error": "Username already exists"}), 400

    # Hash the password before storing
    hashed_password = generate_password_hash(password)

    # Create user document
    user_doc = {
        "username": username,
        "password": hashed_password
    }

    # Insert the new user into the database
    inserted_user = user_collection.insert_one(user_doc)

    # Return success response
    return jsonify({
        "message": "User created successfully",
        "user_id": str(inserted_user.inserted_id)  # Return user ID as a string
    }), 201