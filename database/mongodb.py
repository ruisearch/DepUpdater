"""all operations on the mongodb which stores the direct dependencies of artifacts"""
import pymongo

from database.constants import MONGO_HOST, MONGO_PORT

class Mongo:

    def __init__(self, db_name, collection_name):
        """set the db name and collection name"""
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None

    def connect(self):
        """connect to the mongodb"""
        self.client = pymongo.MongoClient(MONGO_HOST, MONGO_PORT)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def insert_document(self, document):
        """insert one document
        Args:
            document (dict): the document to be inserted
        """
        result = self.collection.insert_one(document)

    def find_document(self, query):
        """Find the document in the collection matching the query.
        Returns:
            document (dict): the document matching the query
        """
        document = self.collection.find_one(query)
        return document

    def close(self):
        """close the connection"""
        self.client.close()
