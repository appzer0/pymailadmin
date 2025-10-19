# utils/db.py

import mysql.connector
from mysql.connector import Error
from libs import config
from datetime import datetime, timedelta
import json
import logging

# Connexion à la base de données
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
        logging.error(f"Erreur de connexion à la base de données: {e}")
        return None

# Exécution d'une requête de type INSERT, UPDATE, DELETE
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
        # La transaction est auto-commitée grâce à autocommit=True
    except Error as e:
        logging.error(f"Erreur lors de l'exécution de la requête: {query} | Params: {params} | Erreur: {e}")
        if connection and connection.is_connected():
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
    return lastrowid

# Récupération de plusieurs résultats
def fetch_all(query, params=None):
    connection = None
    cursor = None
    results = []
    try:
        connection = get_db_connection()
        if connection is None:
            return results
        cursor = connection.cursor(dictionary=True)  # Retourne des dictionnaires
        cursor.execute(query, params)
        results = cursor.fetchall()
    except Error as e:
        logging.error(f"Erreur lors de la récupération des données: {query} | Params: {params} | Erreur: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
    return results
