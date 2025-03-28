from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from v1.about_info_services import (LanguageAboutInfo,
    create_about_info, delete_about_info,
    get_about_info_by_lang,
    get_all_about_info,
    update_about_info,
    convert_object_id,
    update_about_info_by_language_and_id
)
from db import about_info_collection
from v1.auth_services import jwt_required

about_bp = Blueprint("about", __name__)

@about_bp.route("/create-about-info", methods=["POST"])
@jwt_required
def create_about_info_endpoint():
    """
    Expects a JSON body with the following structure:
    {
        "language": "en",
        "content": {
            "title": "Our Mission: Simplify Your Travel Planning",
            "paragraphs": ["Paragraph 1", "Paragraph 2", ...]
        }
    }
    
    Each language entry is stored as a separate document.
    If the document exists, it will delete the existing record and insert a new one.
    If the document does not exist, it will insert a new one.
    """
    try:
        inserted_docs = []
        data = request.get_json()

        for language_code, content in data.items():
            # Create the LanguageAboutInfo object using the received data
            about_info = LanguageAboutInfo(language=language_code, content=content)

            # Construct the document to insert or update
            doc_to_insert = {
                "language": about_info.language,
                "title": about_info.content.title,
                "paragraphs": about_info.content.paragraphs,
            }

            # Check if the document already exists in the database for the language
            existing_doc = get_about_info_by_lang(about_info_collection, language_code)
            
            if existing_doc:
                # Delete the existing document if found
                delete_about_info(about_info_collection, existing_doc["_id"])

            # Insert the new document (upsert behavior)
            inserted = create_about_info(about_info_collection, doc_to_insert)
            inserted = convert_object_id(inserted)  # Convert ObjectId to string
            inserted_docs.append(inserted)

        return jsonify({"inserted": inserted_docs}), 201

    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# GET endpoint for a specific language
@about_bp.route("/about-info/<language>", methods=["GET"])
def get_about_info_by_language(language):
    doc = get_about_info_by_lang(about_info_collection, language)
    if doc:
        return jsonify(convert_object_id(doc)), 200
    else:
        return jsonify({"error": "Not found"}), 404

# GET endpoint to fetch all About-info entries
@about_bp.route("/about-info", methods=["GET"])
def get_all_about_info_endpoint():
    docs = get_all_about_info(about_info_collection)
    # Optionally, transform list into a languages dict
    result = {"languages": {}}
    for doc in docs:
        convert_object_id(doc)
        lang_code = doc.get("language")
        if lang_code:
            # Remove the language field from the inner object to avoid redundancy
            doc_copy = dict(doc)
            doc_copy.pop("language", None)
            result["languages"][lang_code] = doc_copy
    return jsonify(result), 200

# PUT endpoint to update an About-info document for a specific language
@about_bp.route("/update-about-info/<language>", methods=["PUT"])
@jwt_required
def update_about_info_endpoint(language):
    """
    Updates an existing About-info document for a specific language.
    The JSON body should include the complete fields you wish to update.
    For example:
    
    {
      "title": "New Mission Statement",
      "paragraphs": [ "New paragraph one", "New paragraph two" ]
    }
    """
    update_data = request.get_json()
    updated_doc = update_about_info(about_info_collection, language, update_data)
    if updated_doc:
        return jsonify(convert_object_id(updated_doc)), 200
    else:
        return jsonify({"error": "Not found"}), 404

@about_bp.route("/update-about-info/<language>/<doc_id>", methods=["PUT"])
@jwt_required
def update_about_info_by_language_and_id_endpoint(language, doc_id):
    """
    Updates an existing About-info document for a specific language and _id.
    The JSON body should include the complete fields you wish to update.
    For example:
    
    {
      "title": "New Mission Statement",
      "paragraphs": [ "New paragraph one", "New paragraph two" ]
    }
    """
    update_data = request.get_json()
    try:
        updated_doc = update_about_info_by_language_and_id(about_info_collection, language, doc_id, update_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if updated_doc:
        return jsonify(convert_object_id(updated_doc)), 200
    else:
        return jsonify({"error": "Not found"}), 404