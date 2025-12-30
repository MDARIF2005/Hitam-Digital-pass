
import firebase_admin
from firebase_admin import credentials, firestore
import os

def init_db():
    """Initializes the Firebase database connection."""
    if not firebase_admin._apps:
        try:
            cred_path = os.path.join(os.path.dirname(__file__), 'firebase-credentials.json')
            if not os.path.exists(cred_path):
                raise FileNotFoundError("Firebase credentials file not found.")
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase DB initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")

def get_user_by_id(user_type, user_id):
    """Fetches a user document from the appropriate collection by its document ID."""
    try:
        db = firestore.client()
        collection_name = f"{user_type}s"
        doc_ref = db.collection(collection_name).document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return None
    except Exception as e:
        print(f"Error fetching user {user_id} from {user_type}: {e}")
        return None

def add_document(collection_name, data, document_id=None):
    """Adds a new document to a specified collection."""
    try:
        db = firestore.client()
        if document_id:
            doc_ref = db.collection(collection_name).document(document_id)
        else:
            doc_ref = db.collection(collection_name).document()
        
        doc_ref.set(data)
        return doc_ref.id # Return the new document's ID
    except Exception as e:
        print(f"Error adding document to {collection_name}: {e}")
        return None

def add_user(role, user_data):
    """Adds a user to the appropriate collection based on their role."""
    collection_name = f"{role}s"
    return add_document(collection_name, user_data)

def get_user_by_email(role, email):
    """Fetches a user from the appropriate collection by their email address."""
    try:
        db = firestore.client()
        collection_name = f"{role}s"
        users_ref = db.collection(collection_name)
        query = users_ref.where('email', '==', email).limit(1)
        results = query.stream()
        for doc in results:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error fetching user by email from {collection_name}: {e}")
        return None
