from flask import Blueprint, request, jsonify
from v1.services import geocode_address, get_all_homepage_texts_from_db, get_route_data, convert_distance, get_air_distance, estimate_flight_time, create_homepage_text,update_document_by_language_and_id,update_homepage_text_by_id,get_newest_homepage_text,get_homepage_text_by_lang,delete_homepage_text, MultiLanguageData, convert_object_id
from pydantic import ValidationError
from v1.auth_services import jwt_required

############## HOMEPAGE INFO #####################


homepage_bp = Blueprint("homepage", __name__)


@homepage_bp.route("/homepage/homepage-texts", methods=["POST"])
@jwt_required
def create_all_texts():
    """
    Expects a JSON body in the shape:
    {
      "languages": {
        "en": {
          "headline": "English headline",
          "intro_paragraph": "...",
          "features": ["...","..."],
          "cta": "..."
        },
        "es": {
          ...
        },
        ...
      }
    }
    Inserts/Upserts each language as a separate document.
    """
    try:
        data = request.get_json()
        multi_text_obj = MultiLanguageData(**data)

        inserted_docs = []
        for lang_code, content in multi_text_obj.languages.items():
            doc_to_insert = {
                "language": lang_code,
                "headline": content.headline,
                "intro_paragraph": content.intro_paragraph,
                "features": content.features,
                "cta": content.cta,
            }
            inserted = create_homepage_text(doc_to_insert)
            inserted = convert_object_id(inserted)  # convert ObjectId to string
            inserted_docs.append(inserted)
        return ({"inserted": inserted_docs}), 201

    except ValidationError as e:
        return ({"error": str(e)}), 400
    except Exception as e:
        return ({"error": str(e)}), 500


@homepage_bp.route("/homepage-texts/<language>", methods=["GET"])
def get_text(language):
    """
    Returns the homepage text for a specific language (if found).
    """
    doc = get_homepage_text_by_lang(language)
    if doc:
        return convert_object_id(doc), 200
    else:
        return jsonify({"error": "Not found"}), 404


@homepage_bp.route("/homepage/homepage-texts", methods=["GET"])
def get_all_texts():
    """
    Returns all documents, combined into a single structure:
    {
      "languages": {
        "en": {
          "headline": "...",
          "intro_paragraph": "...",
          "features": [...],
          "cta": "...",
          "created_at": "...",
          "updated_at": "..."
        },
        "es": {
          ...
        },
        ...
      }
    }
    """
    docs = get_all_homepage_texts_from_db()  # Returns a list of documents

    result = {"languages": {}}
    for doc in docs:
        # Convert _id to string
        convert_object_id(doc)

        lang_code = doc.get("language")
        # Remove the language key from the doc that we'll embed
        # so we don't duplicate it in the result dict
        doc_for_output = dict(doc)
        doc_for_output.pop("language", None)

        result["languages"][lang_code] = doc_for_output

    return jsonify(result), 200


@homepage_bp.route("/homepage/homepage-texts/newest", methods=["GET"])
def get_newest_text():
    """
    Returns the single most recently updated or created homepage text,
    sorted by updated_at descending.
    """
    doc = get_newest_homepage_text()
    if doc:
        return jsonify(convert_object_id(doc)), 200
    else:
        return jsonify({"error": "No documents found"}), 404


@homepage_bp.route("/homepage-texts/<language>/<doc_id>", methods=["PUT"])
@jwt_required
def update_text_by_language_and_id(language, doc_id):
    update_data = request.get_json()
    try:
        updated_doc = update_document_by_language_and_id(language, doc_id, update_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if updated_doc:
        return jsonify(convert_object_id(updated_doc)), 200
    else:
        return jsonify({"error": "Not found"}), 404


@homepage_bp.route("/homepage-texts/<language>", methods=["DELETE"])
@jwt_required
def delete_text(language):
    deleted = delete_homepage_text(language)
    if deleted:
        return jsonify({"message": "Deleted"}), 200
    else:
        return jsonify({"error": "Not found"}), 404
    
   
@homepage_bp.route("/homepage-texts/id/<doc_id>", methods=["PUT"])
@jwt_required
def update_text_by_id(doc_id):
    update_data = request.get_json()
    updated_doc = update_homepage_text_by_id(doc_id, update_data)
    
    if updated_doc:
        return jsonify(convert_object_id(updated_doc)), 200
    else:
        return jsonify({"error": "Not found or invalid ID"}), 404
    


