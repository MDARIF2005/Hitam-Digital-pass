import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY_PATH')
    FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL')
