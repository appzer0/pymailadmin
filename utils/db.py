# utils/db.py

import mysql.connector
from mysql.connector import Error
from libs import config
from datetime import datetime, timedelta
import json
import logging

# Database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=config['db']['host'],
            database=config['db']['dbname'],
            user=config['db']['username'],
            password=config['db']['password'],
            charset=config['db']['charset'],
            autocommit=True
        )
        return connection
    except Error as e:
        logging.error(f"Error when connecting to database: {e}")
        return None

# INSERT, UPDATE, DELETE requests execution
def execute_query(query, params=None):
    connection = None
    cursor = None
    lastrowid = None
    try:
        connection = get_db_connection()
        if connection is None:
            return None
        cursor = connection.cursor()
        cursor.execute(query, params)
        lastrowid = cursor.lastrowid
    except Error as e:
        logging.error(f"Error when executing SQL request: {query} | Params: {params} | Error: {e}")
        if connection and connection.is_connected():
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
    return lastrowid

# Fetch results
def fetch_all(query, params=None):
    connection = None
    cursor = None
    results = []
    try:
        connection = get_db_connection()
        if connection is None:
            return results
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        results = cursor.fetchall()
    except Error as e:
        logging.error(f"Error when fetching data: {query} | Params: {params} | Error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
    return results
