import pyodbc
from config import Config

def get_db_connection():
    conn = pyodbc.connect(Config.get_connection_string())
    return conn