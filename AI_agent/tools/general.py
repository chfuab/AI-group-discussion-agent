from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from langchain.tools import tool
import os
from typing import Optional

class GeneralTools:

    @tool   
    def code_executor(self, is_querying_database: bool, 
                      code: str, 
                      is_image: bool,
                      custom_result: str=None):

        ''' This method try executing the python code in string format. If the code is successfully run, it will return the result, or it will return an error message.

        Args:
            is_querying_database: whether or not the code contains commands querying or writing a database
            code: The full python code in string format to be executed 
            is_image: whether or not the code is storing base64 encoded image string in the last variable. 
            custom_result: name of the custom result variable returned from the code defined by user if the code is for purposes other than querying or writing database

        Returns:
            Error message if code failed to be executed, or query result if the code is sucessfully run and is for querying or writing a database, or
            custom result defined by the user returned from the code if teh code is successfully run
        '''
        try:
            pass
            
        except Exception as e:
            return f"Error: {e}"