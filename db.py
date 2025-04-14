import os
from pymongo import MongoClient

MONGO_URI = os.getenv("DATABASE_URL")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

homepage_texts_collection = db["homepage_texts"]
about_info_collection = db["about_info"]
privacy_policy_collection = db["privacy_policy"]
user_collection = db['users']
city_collection = db["countries_cities"]