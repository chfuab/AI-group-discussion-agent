from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from langchain.tools import tool
import psycopg2
from psycopg2 import OperationalError, DatabaseError
import mysql.connector
from mysql.connector import errorcode
import os
import json
from typing import Optional
from collections import defaultdict
from ..tools.general import GeneralTools
from ..sql_commands.database_metadata import (
    get_tables_and_columns_pg, 
    get_tables_and_columns_mysql,
    get_relationships_pg,
    get_relationships_mysql,
)
from typing import Literal
import re

class Database:
    def __init__(self):
        self.db_config_path = "../agent/config/database_config.json"

        with open(self.db_config_path) as f:
            self.db_config = json.load(f)

        self.metadata = defaultdict(dict)
        self.metadata_noSQL = defaultdict(dict)

    def connect_and_test_database(self):
        '''This function is to establish connection, as well as test connection to the database which is a necessary step before querying the database

        Args:
            

        Returns:
            Selected database (self.db)
        '''
        for key, _ in self.db_config.items():
            if key == "PostgreSQL":
                self.conn_pg = []
                for db, db_details in self.db_config[key]["database"]:
                    self.conn_pg.append(psycopg2.connect(**self.db_config[key]["database"][db]))

            elif key == "MongoDB":
                client = MongoClient(self.db_config[key]["local_uri"])
                
            elif key == "MySQL":
                self.conn_mysql = []
                for db, db_details in self.db_config[key]["database"]:
                    self.conn_mysql.append(mysql.connector.connect(**self.db_config[key]["database"][db]))

        try:
            conn_all = self.conn_pg.extend(self.conn_mysql)
            len_conn_pg = len(self.conn_pg)

            # test connection of PostgreSQL and MySSQL database
            for i, conn in enumerate(conn_all):
                cursor = conn.cursor()
                if i <= len_conn_pg - 1:
                    cursor.execute("SELECT current_database();")
                    current_db = cursor.fetchone()[0]
                else:
                    cursor.execute("SELECT database();")
                    current_db = cursor.fetchone()[0]
                print(f"  Currently connected to: {current_db}")

            # test connection to MongoDB database
            client.admin.command('ping')
            print("Success: Successfully connected to MongoDB!")

        except OperationalError as e_op:
            print(f"Operational error connecting to PostgreSQL database: {e_op}")
            
        except DatabaseError as e_db:
            print(f"Database error executing query on PostgreSQL database: {e_db}")
        
        except ConnectionFailure as e_conn:
            print("Error: Server not available or network timeout.")

        except OperationFailure as e_op_noSQL:
            print(f"Error: Authentication failed or invalid permissions.\nDetails: {e_op_noSQL}")

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("MySQL: Invalid username or password.")

            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("MySQL: Database does not exist.")

            else:
                print(f"MySQL: Connection failed: {err}")

        except Exception as e:
            print(f"Unexpected error occurred: {e}")
        
        finally:
            self.all_SQL_connection = conn_all
            self.noSQL_client = client
            self.len_conn_pg = len_conn_pg
    
    def list_tables_for_SQL_databases(self):
        """
        Objective: list all tables and columns for each database

        input: N/A
        output: tables, columns & relations for all databases in json format
        """
        all_db = defaultdict(dict)
        for i, conn in enumerate(self.conn_all):
            cursor = conn.cursor()

            if i <= self.len_conn_pg - 1: # for PostgreSQL database
                sql_str = "SELECT datname FROM pg_database;"
                
                cursor.execute(sql_str)
                databases = cursor.fetchall()

                all_db["PostgreSQL"][f"db_{i}"] = [db[0] for db in databases]

                self.metadata["database"] = {}
                # tables and columns
                for database_name in all_db["PostgreSQL"][f"db_{i}"]:
                    self.sql_filling_metadata(cursor=cursor, database_name=f"{database_name}_db_{i}-PostgreSQL", database_type="postgresql")
                    
            else: # for MySQL database
                sql_str = "SHOW DATABASES;"

                cursor.execute(sql_str)
                databases = cursor.fetchall()

                all_db["MySQL"][f"db_{i - self.len_conn_pg}"] = [db[0] for db in databases]
                for database_name in all_db["MySQL"][f"db_{i}"]:
                    self.sql_filling_metadata(cursor=cursor, database_name=f"{database_name}_db_{i - self.len_conn_pg}-MySQL", database_type="mysql")
            
        return self.metadata
    
    def list_collections_and_fields_noSQL_databases(self):
        db_names = self.noSQL_client.list_database_names()

        for db in db_names:
            database = self.noSQL_client[db]
            collection_names = database.list_collection_names()

            for collect in collection_names:
                sample = database[collect].find_one()
                field_paths = self.get_all_field_paths(sample)

                self.metadata_noSQL[database]["database_type"] = "MongoDB"
                self.metadata_noSQL[database]["collection"] = collect
                self.metadata_noSQL[database]["known_fields"] = field_paths
                self.metadata_noSQL[database]["query_intent"] = ""

        return self.metadata_noSQL


    def sql_filling_metadata(self, cursor, database_name, database_type: str):
        db_type = {}
        db_type.update({database_name: {}})
        db_type[database_name]["database_type"] = database_type
        self.metadata["database"] = db_type

        cursor.execute(get_tables_and_columns_pg, (database_name,))

        tables = {}
        for table, column in cursor.fetchall():
            tables.update({table:{"columns":[]}})
            tables[table]["columns"].append(column)
        self.metadata["database"][database_name]["tables"] = tables

        cursor.execute(get_relationships_pg, (database_name,))

        relationships = []
        for from_table, from_col, to_table, to_col in cursor.fetchall():
            relationships.append({
                "from": f"{database_name}.{from_table}.{from_col}",
                "to": f"{database_name}.{to_table}.{to_col}"
            })
        self.metadata["database"][database_name]["relationships"] = relationships
        

    def get_all_field_paths(self, doc, parent_key=''):
        """Recursively extract all field paths from a document"""
        fields = []

        for key, value in doc.items():
            # Skip MongoDB internal fields if desired
            if key == '_id':
                continue

            current_path = f"{parent_key}.{key}" if parent_key else key

            if isinstance(value, dict):
                # Recursively traverse nested documents
                fields.extend(self.get_all_field_paths(value, current_path))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Sample first item in array for nested fields
                fields.extend(self.get_all_field_paths(value[0], f"{current_path}[]"))
            else:
                fields.append(current_path)

        return fields
    
    @tool
    async def execute_SQL_command(self, database_name: str, sql_cmd: str):
        i = re.findall(r'\d+', database_name)[-1]    # the name contains only one number
        db_type = database_name.split("-")[-1]

        if db_type == "PostgreSQL":
            conn = self.all_SQL_connection[i]
        elif db_type == "MySQL":
            conn = self.all_SQL_connection[i + self.len_conn_pg]

        try:
            cursor = conn.cursor()
            cursor.execute(sql_cmd)
            res = cursor.fetchall()

            return res
        except Exception as e:
            return f"Error: {e}"
        finally:
            conn.close()

    @tool
    async def execute_NoSQL_command(self, method_str: Literal["find", "find_one", "aggregate", "distinct", 
                                                              "count_documents", "estimated_document_count"], 
                                    database_name: str, collection: str, nosql_cmd: str):
        try:
            coll = self.noSQL_client[database_name][collection]
            result_doc = getattr(coll, method_str)(nosql_cmd)
            return result_doc
        except Exception as e:
            return f"Error: {e}"

