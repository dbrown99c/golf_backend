import pymongo
from bson import ObjectId
import datetime
from pytz import timezone
import config

class MongoConnection:
    def __init__(self):
        self.client = pymongo.MongoClient("10.7.0.100", 3001)
        self.db = self.client.puttnation
        self.op_dict = {"==": "eq", ">=": "gte", ">": "gt", "in": "in",
                        "<=": "lte", "<": "lt", "!=": "ne", "nin": "nin"}

    @staticmethod
    def convert_id(**kwargs):
        if kwargs.get("_id"):
            kwargs["id"] = str(kwargs.pop("_id"))
        return kwargs

    def create_document(self, collection, **kwargs):
        self.db[collection].insert_one(kwargs)
        kwargs = self.convert_id(**kwargs)
        return kwargs

    def update_document(self, collection, document_id, object_id=True, **kwargs):
        kwargs.pop("id", None)
        if object_id:
            self.db[collection].update_one({"_id": ObjectId(document_id)}, {"$set": kwargs})
        else:
            self.db[collection].update_one({"name": document_id}, {"$set": kwargs})
        kwargs = self.convert_id(**kwargs)
        return kwargs

    def upsert_document(self, collection, document_id, object_id=True, **kwargs):
        kwargs.pop("id", None)
        if object_id:
            self.db[collection].update_one({"_id": ObjectId(document_id)}, {"$set": kwargs}, upsert=True)
        else:
            self.db[collection].update_one({"_id": document_id}, {"$set": kwargs}, upsert=True)
        kwargs = self.convert_id(**kwargs)
        return kwargs

    def query_document(self, collection, param, operator, value, return_first=True):
        filter_condition = {f"${self.op_dict[operator]}": value}
        query_ref = self.db[collection].find({param: filter_condition})
        res = [x for x in query_ref]
        if len(res) > 0 and return_first:
            doc_dict = self.convert_id(**res[0])
            return doc_dict
        elif len(res) > 0:
            doc_list = [self.convert_id(**res[i]) for i, x in enumerate(res)]
            return doc_list
        if return_first:
            return None
        return []

    def get_document(self, collection, document_id):
        res = self.db[collection].find_one({"_id": ObjectId(document_id)})
        if res:
            res = self.convert_id(**res)
            return res
        return None

    def get_collection(self, collection):
        query_ref = self.db[collection].find()
        res = [self.convert_id(**x) for x in query_ref]
        return res

    def delete_document(self, collection, document_id, object_id=True):
        if object_id:
            res = self.db[collection].delete_one({"_id": ObjectId(document_id)})
        else:
            res = self.db[collection].delete_one({"_id": document_id})
        return None

    def delete_old_docs(self, collection):
        weekago = datetime.datetime.now(tz=timezone(config.timezone)) - datetime.timedelta(days=7)
        res = self.db[collection].delete_many({"created_at": {"$lt": weekago}})


# db = MongoConnection()
# db.db.drop_collection("alarms")
# print(db.get_collection("circus"))
# print(db.get_collection("alarms"))
# print(db.get_collection("pub"))
# res = db.db["config"].find_one('timezone')
# print(res)
# db.create_document("config", **{"timezone":"US/Eastern", "_id": "timezone"})
# db.update_document("pub", "644d850504fd861f26a59cff", object_id=True, **{"created_at": datetime.datetime(2023, 4, 29, 16, 17, 52, 559000)})
# db.delete_old_docs("pub")
# print(db.get_collection("pub"))