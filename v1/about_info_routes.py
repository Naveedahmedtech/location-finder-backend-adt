from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from v1.about_info_services import (LanguageAboutInfo, MultiLanguageAboutInfo,
    create_about_info, replace_about_info_lang,
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
def create_about_info_bulk():
    """
    POST /create-about-info-bulk
    Expects JSON like:
    {
      "languages": {
        "en": {
          "title": "Our Mission: ...",
          "paragraphs": [...]
        },
        "es": { ... },
        "pt": { ... },
        "fr": { ... }
      }
    }
    For each language, we delete old doc + insert a new doc in 'about_info' collection.
    Returns array of final inserted docs.
    """
    try:
        data = request.get_json()
        multi_about = MultiLanguageAboutInfo(**data)  
        # shape: { languages: { "en": {title, paragraphs}, "es": {...}, ... } }

        inserted_docs = []
        for lang_code, single_info in multi_about.languages.items():
            doc_to_insert = {
                "title": single_info.title,
                "paragraphs": single_info.paragraphs,
            }
            replaced_doc = replace_about_info_lang(collection=about_info_collection, lang_code=lang_code, doc_data=doc_to_insert)
            replaced_doc = convert_object_id(replaced_doc)  # optional
            inserted_docs.append(replaced_doc)

        return jsonify({"inserted": inserted_docs}), 201

    except ValidationError as ve:
        return jsonify({"error": str(ve)}), 400
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