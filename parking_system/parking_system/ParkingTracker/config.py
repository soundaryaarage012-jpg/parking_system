import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "smart-parking-secret")


class Config:
    SECRET_KEY = SECRET_KEY
    DATABASE = DB_PATH
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
