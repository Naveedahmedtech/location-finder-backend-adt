from typing import List, Optional,Dict
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
from pydantic import BaseModel

class SingleLanguageAboutInfo(BaseModel):
    title: str
    paragraphs: List[str]

class MultiLanguageAboutInfo(BaseModel):
    languages: Dict[str, SingleLanguageAboutInfo]
class LanguageAboutInfo(BaseModel):
    language: str
    content: SingleLanguageAboutInfo


def convert_object_id(doc: dict) -> dict:
    """
    Converts the _id field from ObjectId to string, if present.
    """
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc

def create_about_info(collection, doc: dict) -> dict:
    """
    Inserts a new document into the About-info collection.
    Adds created_at and updated_at timestamps.
    """
    now = datetime.utcnow()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = collection.insert_one(doc)
    return collection.find_one({"_id": result.inserted_id})

def get_about_info_by_lang(collection, language: str) -> Optional[dict]:
    """
    Retrieves a single About-info document based on language.
    """
    return collection.find_one({"language": language})

def get_all_about_info(collection) -> List[dict]:
    """
    Returns all documents in the About-info collection.
    """
    return list(collection.find({}))

def update_about_info(collection, language: str, update_data: dict) -> Optional[dict]:
    """
    Updates an About-info document for a given language.
    Updates only the provided fields (plus updated_at timestamp).
    """
    update_data["updated_at"] = datetime.utcnow()
    updated_doc = collection.find_one_and_update(
        {"language": language},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    return updated_doc

def update_about_info_by_language_and_id(collection, language: str, doc_id: str, update_data: dict) -> dict:
    """
    Updates an About-info document using both its _id and language.
    
    Args:
        collection: The MongoDB collection.
        language (str): The language value to match.
        doc_id (str): The document _id as a string.
        update_data (dict): The fields to update.
        
    Returns:
        dict: The updated document, or None if not found.
        
    Raises:
        ValueError: If doc_id is not a valid ObjectId.
    """
    try:
        object_id = ObjectId(doc_id)
    except Exception:
        raise ValueError("Invalid ObjectId format")
    
    update_data["updated_at"] = datetime.utcnow()
    filter_query = {"_id": object_id, "language": language}
    
    updated_doc = collection.find_one_and_update(
        filter_query,
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    return updated_doc