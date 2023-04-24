import firebase_admin
from firebase_admin import firestore, auth, credentials
import os


class FirestoreConnection:
    def __init__(self):
        self.cred = credentials.Certificate(os.environ["PUTTNATION_CREDS"])
        self.app = firebase_admin.initialize_app(self.cred)
        self.db = firestore.client()
        self.auth = auth.Client(self.app)

    def create_document(self, collection, **kwargs):
        update_time, doc_ref = self.db.collection(collection).add(kwargs)
        return {"id": doc_ref.id, **doc_ref.get().to_dict()}

    def upsert_to_document(self, collection, document_id, **kwargs):
        kwargs.pop("id", None)
        doc_ref = self.db.collection(collection).document(document_id)
        doc = doc_ref.get().to_dict()
        if doc:
            doc_ref.set(kwargs, merge=True)
            document = doc_ref.get().to_dict()
            return {"id": document_id, **document}
        return None

    def query_document(self, collection, param, operator, value, return_first=True):
        doc_ref = self.db.collection(collection).where(param, operator, value)
        doc = doc_ref.get()
        if len(doc) > 0 and return_first:
            doc_dict = doc[0].to_dict()
            return {"id": doc[0].id, **doc_dict}

        elif len(doc) > 0:
            doc_list = [{"id": r.id, **r.to_dict()} for r in doc]
            return doc_list
        if return_first:
            return None
        return []

    def get_document(self, collection, document_id):
        """ Returns a None if there is no document found """
        doc_ref = self.db.collection(collection).document(document_id)
        document = doc_ref.get().to_dict()
        if document:
            return {"id": document_id, **document}
        return None

    def get_collection(self, collection):
        col_ref = self.db.collection(collection)
        collection = col_ref.get()
        collection_array = []
        for doc in collection:
            collection_array.append({"id": doc.id, **doc.to_dict()})
        return collection_array
