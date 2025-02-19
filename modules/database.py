import pymongo
import os

client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client["hirokesbot"]

def add_banned_word(word):
    """Menambahkan kata terlarang ke database"""
    db.banned_words.insert_one({"word": word.lower()})

def remove_banned_word(word):
    """Menghapus kata terlarang dari database"""
    db.banned_words.delete_one({"word": word.lower()})
