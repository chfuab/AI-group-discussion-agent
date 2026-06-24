from pydantic import BaseModel, Field
from langgraph.graph import MessagesState
from typing import List, Annotated
import operator
from collections import defaultdict

class QeuryingDatabaseState(MessagesState):
    ''' A set of data passed into or returned from querying the database'''

    with_error: bool = Field(description=
                             "whether or not the query to the database returns error message",
                             default=False)
    error_message: str = Field(description=
                               "the error message arisen if the querying to the database failed")
    expected_outcome: str = Field(description=
                                  "the target result of the query. If the querying result deviated from this target, it will be re-written or modified")
    query_plan: str = Field(description=
                            "the self-planning plan generated when the LLM is prompted to generated query_code")
    query_code: str = Field(description=
                         "the code for querying the database given 'human' prompt")
    feedback: List[str] = Field(description=
                         "feedback to regenerate query_plan and query_code",
                         default=[""])
    original_statement: str = Field(description=
                                    "original conditions which will be decomposed into verifiable statement and analysis statement", 
                                    default="")
    verifiable_prompt:str = Field(description=
                                    "the statements translatable into querying command of the databases",
                                           default=[])
    analysis_statement:str = Field(description=
                                   "specify what to get or achieve after analysis on the query_results",
                                          default=[])
    verification_decision: List[bool] = Field(description=
                               "whether the original input statement statisfied or not",
                               default=True)
    verification_result: List[str] = Field(description="the rewritten original statement after analysis on the results queried from database",
                                                    default="")    
    retry:int = Field(description=
                      "Number of retry of database querying when error messages occur",
                      default=0)
    role: str = Field(description="role of the agent",
                      default="")
    failure_remarks: defaultdict = Field(description="remarks indicating that why the verification is failed",
                         default="")
    
class QeuryingDatabaseWrapperState(MessagesState):
    original_statement: str = Field(description=
                                    "original conditions which will be decomposed into verifiable statement and analysis statement", 
                                    default="")    
    verification_decision: Annotated[List[bool], operator.add] = Field(description=
                               "whether the original input statement statisfied or not",
                               default=True)
    verification_result: Annotated[List[str], operator.add] = Field(description="the rewritten original statement after analysis on the results queried from database",
                                                    default="")  

class SelectingDatabaseState(MessagesState):
    db_config_path: str = Field(default=
                                "./config/database_config.json",
                                description="location of the database config json file")