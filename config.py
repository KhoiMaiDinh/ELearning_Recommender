from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    DB_SERVER = os.getenv('DB_SERVER')
    DB_DATABASE = os.getenv('DB_DATABASE')
    DB_USERNAME = os.getenv('DB_USERNAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    @staticmethod
    def get_connection_string():
        return f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={Config.DB_SERVER};DATABASE={Config.DB_DATABASE};UID={Config.DB_USERNAME};PWD={Config.DB_PASSWORD}'