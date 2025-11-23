import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_secret_key_123456'
    MONGO_URI = "mongodb://localhost:27017/quanly_xekhach"
