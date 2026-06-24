from pydantic import BaseModel, Field
from langgraph.graph import MessagesState
from typing import Annotated, List, TypedDict
import operator

class CheckFeasibilityState(MessagesState):
    factors_to_be_verified: List[str] = Field(description="the conditions to be verified by querying database. Condition determining it are all known or is none", 
                                              default=[""])
    factors_verified: List[str] = Field(description="the conditions verified after querying database.", 
                                              default=[])
    combined_verification_result: str = Field(description="concatenated strings where each of them is the verification result after querying database ", 
                                              default="")
    all_factors_listed: str = Field(description="json string listing out all factors where for each of them there are factors causing it and factors caused by it",
                                    default="")
    verification_result: Annotated[List[str], operator.add] = Field(description="collection of analyzed result quried from databases", 
                                                              default=[""])
    verification_decision: Annotated[List[bool], operator.add] = Field(description="collection of true/false decision made on analyzed result quried from databases", 
                                                              default=[""])
    final_judgement: bool = Field(description="final_judgement returns True if no 'False' existed in the collection of state['intermediate_decision']",
                                  default=True)
    all_explanation: dict[str, dict[str]] = Field(description="all explanation for why a set of conditions failed can lead to the negation of the ideas",
                                       default=[""])