from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["HACK_db"]
conversations = db["conversations"]
users = db["users"]
verif_col= db["verifications"]
 