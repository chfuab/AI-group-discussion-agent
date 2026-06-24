from pydantic import BaseModel, Field
from typing import List

class PromptClarification(BaseModel):
    verifiable_prompt: str = Field(description="the statements translatable into querying command of the databases", 
                                      default="")
    analysis_statement: str = Field(description="specify what to get or achieve after analysis on the query_results",
                                    default="")
    
class QueryDatabaseOutput(BaseModel):
    query_code: str = Field(description=
                            "the code for querying the database given 'human' prompt",
                            default="")
    query_plan: str = Field(description=
                            "the self-planning plan generated when the LLM is prompted to generated query_code",
                            default="")
    
    
class Feedback(BaseModel):
    feedback: str = Field(description="feedback to regenerate query_plan and query_code",
                          default="")
    retry: int = Field(description="No. of retry of generating SQL / NoSQL query after error messages of execution occur",
                       default=0)
    
class Analysis(BaseModel):
    verification_decision: List[bool] = Field(description="whether the original input statement statisfied or not",
                               default=True)
    verification_result: List[str] = Field(description="the rewritten original statement after analysis on the results queried from database",
                                                    default="")
    
class ListAllFactors(BaseModel):
    all_factors: List[str] = Field(description="json string listing out all factors where for each of them there are factors causing it and factors caused by it",
                                    default="")
    
class Explanation(BaseModel):
    explanation: str = Field(description="explanation for why a specific condition failed can lead to the negation of the ideas",
                             default="")