import pymongo
import os

mongo_uri = os.environ["MONGO_URI"]


class MongoWrapper:
    def __init__(self):
        # TODO: Make this async
        self.db = pymongo.MongoClient(mongo_uri)["jassa"]
