from langgraph.graph import END, START, StateGraph, Send
from langgraph.types import Command
from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    HumanMessage,
)
from ..agent_graphs.sub_graphs.query_databases import QueryDatabases
from ..agent_graphs.sub_graphs.query_databases import query_db_wrapper

from ..config.model_config import DeepSeekConfig
from ..states.check_feasibility import CheckFeasibilityState
from ..prompts.system_prompts import (
    list_factors_prompt, 
    explain_prompt,
)
from ..config.output_config import (
    ListAllFactors,
    Explanation
    )
import json
from typing import Annotated, List, TypedDict
from collections import defaultdict

class CheckFeasibility:
    def __init__(self):
        self.query_db = QueryDatabases(max_retry=10)
        self.sql_db_metadata = self.query_db.db_tools.list_tables_for_SQL_databases()
        self.nosql_db_metadata = self.query_db.db_tools.list_collections_and_fields_noSQL_databases()

        self.configurable_model = init_chat_model(configurable_fields=("model", "max_tokens", 
                                                                       "temperature", "api_key"))
        self.deepseek_model_config = {
            "model": DeepSeekConfig.model,
            "max_tokens": DeepSeekConfig.max_tokens,
            "temperature": DeepSeekConfig.temperature,
            "api_key": DeepSeekConfig.api_key,
        }

    async def factors_for_proposal(self, state: CheckFeasibilityState):
        """
        List out conditions for the user proposal. The conditions must be satisfied for the proposal to be workable
        """
        list_factors_model = (self.configurable_model
                       .with_config(self.deepseek_model_config)
                       .with_structured_output(ListAllFactors))
        
        full_prompt = list_factors_prompt.format(
           original_ideas=state.get("messages")[0],
           combined_verification_result=state.get("combined_verification_result", "")
        )
        response = list_factors_model.ainvoke([HumanMessage(content=full_prompt)])

        return {"all_factors_listed": response.get("all_factors")}

    async def gather_verifiable_factors(self, state: CheckFeasibilityState):
        factors_to_be_verified = state.get("factors_to_be_verified", [""])
        factors_verified = state.get("factors_verified", [""])

        all_factors = json.loads(state.get("all_factors_listed"))
        
        for i, condition in enumerate(all_factors["conditions"]):
            if condition not in factors_verified:
                if len(condition["causing_conditions"]) > 0:
                    cause_conds = [1 if item in factors_verified else 0 for item in condition["causing_conditions"]]

                    if sum(cause_conds) == len(condition["causing_conditions"]):
                        factors_to_be_verified.append(condition)
                else:
                    factors_to_be_verified.append(condition)

        return {"factors_to_be_verified": factors_to_be_verified}
    
    async def parallel_execution(self, state: CheckFeasibilityState) -> List[Send]:
        # using Send
        return [
            Send(node="query_db_wrapper", arg={"original_statement": item["the_condition"]}) 
            for item in state["factors_to_be_verified"]
            ]
    
    async def aggregate_execution_results(self, state: CheckFeasibilityState):
        all_factors_with_details = json.loads(state["all_factors_listed"])["conditions"]
        num_all_factors = len(all_factors_with_details)

        if (len(state["verification_result"]) < num_all_factors 
            and (False not in state["verification_decision"])):
            return Command(
                goto="factors_for_proposal",
                update={
                    "factors_verified": state["factors_verified"].extend(state["factors_to_be_verified"]),
                    "factors_to_be_verified": [""],
                    "combined_verification_result": "".join(state["verification_result"]),
                    }
            )
        elif (len(state["verification_result"]) >= num_all_factors 
            and (False not in state["verification_decision"])):
            return Command(
                goto=END,
                update={
                    "final_judgement": True
                }
            )
        else:
            return Command(
                goto="explain_ideas_not_satisfied",
                update={
                    "final_judgement": False,
                }
            )
    async def explain_ideas_not_satisfied(self, state: CheckFeasibilityState):
        explain_model = (self.configurable_model
                       .with_config(self.deepseek_model_config)
                       .with_structured_output(Explanation))

        all_exp = defaultdict()
        for decision, result in zip(state["verification_decision"], state["verification_result"]):
            if not decision:
                full_prompt = explain_prompt.format(
                    original_ideas=state.get("messages")[0],
                    verification_result=result
                )
                response = explain_model.ainvoke([HumanMessage(content=full_prompt)])
                all_exp.update({
                    f"{result}": response.explanation,
                })
        return Command(
            goto=END,
            update={"all_explanation": all_exp}
        )

check_feasibility_builder = StateGraph(CheckFeasibilityState)
check_feasibility_builder.add_node("gather_verifiable_factors", CheckFeasibility.gather_verifiable_factors)
check_feasibility_builder.add_node("query_db_wrapper", query_db_wrapper)
check_feasibility_builder.add_node("aggregate_results", CheckFeasibility.aggregate_execution_results)

check_feasibility_builder.add_edge(START, "gather_verifiable_factors")
check_feasibility_builder.add_conditional_edges(
    source="gather_verifiable_factors",
    path=CheckFeasibility.parallel_execution,
    path_map=["query_db_wrapper"]
)
check_feasibility_builder.add_edge("query_db_wrapper", "aggregate_results")
