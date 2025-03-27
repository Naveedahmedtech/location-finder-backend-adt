from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from v1.auth_services import jwt_required
from v1.privacy_policy_services import (LanguagePrivacyPolicy, MultiLanguagePrivacyPolicy,
    create_privacy_policy, replace_privacy_policy_doc,
    get_privacy_policy_by_lang,
    get_all_privacy_policies,
    update_privacy_policy,
    update_privacy_policy_by_language_and_id,
    convert_object_id
)

privacy_bp = Blueprint("privacy", __name__)

@privacy_bp.route("/create-privacy-policy", methods=["POST"])
@jwt_required
def create_privacy_policy_endpoint():
    """
    Expects JSON e.g.:
    {
      "language": "en",
      "content": { 
        "effective_date": "...", "introduction": "...", etc.
      }
    }
    - Delete old doc for that language (if exists)
    - Insert new doc
    - Return final doc
    """
    try:
        data = request.get_json()
        policy_data = LanguagePrivacyPolicy(**data)  # Pydantic validation

        doc_to_insert = {
            "effective_date": policy_data.content.effective_date,
            "introduction": policy_data.content.introduction,
            "information_we_collect": policy_data.content.information_we_collect,
            "how_we_use_info": policy_data.content.how_we_use_info,
            "cookies": policy_data.content.cookies,
            "third_party_services": policy_data.content.third_party_services,
            "data_security": policy_data.content.data_security,
            "your_rights": policy_data.content.your_rights,
            "changes": policy_data.content.changes,
            "contact_us": policy_data.content.contact_us
        }

        # Call the service function
        replaced_doc = replace_privacy_policy_doc(
            language=policy_data.language,
            doc_data=doc_to_insert
        )

        # Convert _id to string if desired
        replaced_doc = convert_object_id(replaced_doc)
        return jsonify({"inserted": replaced_doc}), 201

    except ValidationError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET endpoint: Retrieve Privacy Policy by language
@privacy_bp.route("/privacy-policy/<language>", methods=["GET"])
def get_privacy_policy_by_language(language):
    doc = get_privacy_policy_by_lang(language)
    if doc:
        return jsonify(convert_object_id(doc)), 200
    else:
        return jsonify({"error": "Not found"}), 404

# GET endpoint: Retrieve all Privacy Policy documents
@privacy_bp.route("/privacy-policy", methods=["GET"])
def get_all_privacy_policy_endpoint():
    docs = get_all_privacy_policies()
    result = {"languages": {}}
    for doc in docs:
        convert_object_id(doc)
        lang_code = doc.get("language")
        if lang_code:
            doc_copy = dict(doc)
            doc_copy.pop("language", None)
            result["languages"][lang_code] = doc_copy
    return jsonify(result), 200

# PUT endpoint: Update Privacy Policy by language (partial update)
@privacy_bp.route("/update-privacy-policy/<language>", methods=["PUT"])
@jwt_required
def update_privacy_policy_endpoint(language):
    """
    Updates an existing Privacy Policy document for a specific language.
    The JSON body should include the fields you wish to update.
    
    For example:
    
    {
      "effective_date": "New effective date",
      "introduction": "New introduction text",
      ...
    }
    """
    update_data = request.get_json()
    updated_doc = update_privacy_policy(language, update_data)
    if updated_doc:
        return jsonify(convert_object_id(updated_doc)), 200
    else:
        return jsonify({"error": "Not found"}), 404

# PUT endpoint: Update Privacy Policy by language and document ID
@privacy_bp.route("/update-privacy-policy/<language>/<doc_id>", methods=["PUT"])
@jwt_required
def update_privacy_policy_by_language_and_id_endpoint(language, doc_id):
    """
    Updates an existing Privacy Policy document for a specific language and _id.
    The JSON body should include the fields you wish to update.
    
    For example:
    
    {
      "effective_date": "New effective date",
      "introduction": "New introduction text",
      ...
    }
    """
    update_data = request.get_json()
    try:
        updated_doc = update_privacy_policy_by_language_and_id(language, doc_id, update_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    if updated_doc:
        return jsonify(convert_object_id(updated_doc)), 200
    else:
        return jsonify({"error": "Not found"}), 404
