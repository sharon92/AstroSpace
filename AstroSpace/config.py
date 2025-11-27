import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    
    TITLE = os.environ.get("TITLE", "AstroSpace")
    MAX_USERS = int(os.environ.get("MAX_USERS", 1))

    UPLOAD_PATH = os.environ.get("UPLOAD_PATH", os.path.abspath("uploads"))

    if "DB_NAME" in os.environ:
        DB_NAME = os.environ['DB_NAME']
    
    if "DB_USER" in os.environ:
        DB_USER = os.environ['DB_USER']
    
    if "DB_PASSWORD" in os.environ:
        DB_PASSWORD = os.environ['DB_PASSWORD']
    
    if "DB_HOST" in os.environ:
        DB_HOST = os.environ['DB_HOST']
    
    if "DB_PORT" in os.environ:
        DB_PORT = int(os.environ['DB_PORT'])