from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "mydb")
    DB_USER = os.getenv("DB_USERNAME", "myuser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")
    
    @staticmethod
    def get_connection_string():
        return f"postgresql+psycopg2://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    