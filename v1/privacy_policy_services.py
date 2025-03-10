from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
from db import privacy_policy_collection


class PrivacyPolicyLanguageData(BaseModel):
    effective_date: str
    introduction: str
    information_we_collect: List[Dict[str, str]]
    how_we_use_info: List[str]
    cookies: str
    third_party_services: str
    data_security: str
    your_rights: str
    changes: str
    contact_us: str

class MultiLanguagePrivacyPolicy(BaseModel):
    languages: Dict[str, PrivacyPolicyLanguageData]


def convert_object_id(doc: dict) -> dict:
    """
    Converts the _id field from ObjectId to string, if present.
    """
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

def create_privacy_policy(doc: dict) -> dict:
    """
    Inserts a new document into the Privacy Policy collection.
    Adds created_at and updated_at timestamps.
    """
    now = datetime.utcnow()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = privacy_policy_collection.insert_one(doc)
    return privacy_policy_collection.find_one({"_id": result.inserted_id})

def get_privacy_policy_by_lang(language: str) -> Optional[dict]:
    """
    Retrieves a single Privacy Policy document by language.
    """
    return privacy_policy_collection.find_one({"language": language})

def get_all_privacy_policies() -> List[dict]:
    """
    Returns all documents in the Privacy Policy collection.
    """
    return list(privacy_policy_collection.find({}))

def update_privacy_policy(language: str, update_data: dict) -> Optional[dict]:
    """
    Updates an existing Privacy Policy document for a given language.
    Uses $set to update only the provided fields and updates the updated_at timestamp.
    """
    update_data["updated_at"] = datetime.utcnow()
    updated_doc = privacy_policy_collection.find_one_and_update(
        {"language": language},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    return updated_doc

def update_privacy_policy_by_language_and_id(language: str, doc_id: str, update_data: dict) -> dict:
    """
    Updates a Privacy Policy document by both its _id and language.
    Raises a ValueError if doc_id is not a valid ObjectId.
    """
    try:
        object_id = ObjectId(doc_id)
    except Exception:
        raise ValueError("Invalid ObjectId format")
    
    update_data["updated_at"] = datetime.utcnow()
    filter_query = {"_id": object_id, "language": language}
    
    updated_doc = privacy_policy_collection.find_one_and_update(
        filter_query,
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    return updated_doc
