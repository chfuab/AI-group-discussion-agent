from ..config.model_config import DeepSeekConfig
from ..config.output_config import (
    PromptClarification,
    QueryDatabaseOutput,
    Feedback,
    Analysis
    )
from ...tools.database import Database
from ..states.querying_or_writing_db import QeuryingDatabaseState, QeuryingDatabaseWrapperState
from ..prompts.system_prompts import (
    feedback_with_err_msg_prompt, 
    gen_query_prompt,
    analysis_prompt,
    clarification_prompt,
)
from ...tools.database import Database
from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    HumanMessage,
    ToolMessage,
    AIMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langgraph.graph import MessagesState
from langgraph.graph import END, START, StateGraph, Send
from typing import Literal, List
import json

class QueryDatabases:
    def __init__(self, max_retry: int=10):
        self.configurable_model = init_chat_model(configurable_fields=("model", "max_tokens", 
                                                                       "temperature", "api_key"))
        self.deepseek_model_config = {
            "model": DeepSeekConfig.model,
            "max_tokens": DeepSeekConfig.max_tokens,
            "temperature": DeepSeekConfig.temperature,
            "api_key": DeepSeekConfig.api_key,
        }

        self.db_tools = Database()
        self.db_tools.connect_and_test_database()
        self.sql_db_metadata = self.db_tools.list_tables_for_SQL_databases()
        self.nosql_db_metadata = self.db_tools.list_collections_and_fields_noSQL_databases()

        self.roles_config_path = "...config/role_agents.json"
        with open(self.roles_config_path) as f:
            self.roles_config = json.load(f)

        self.max_retry = max_retry

    async def jobs_assignment(self, state: QeuryingDatabaseWrapperState) -> List[Send]:
        
        return [Send(
            node="query_database_subgraph", 
            arg={
                "original_statement": get_buffer_string(state.get("original_statement", "")),
                "role": role
                }) 
            for role in self.roles_config.keys()]

    async def prompt_clarification(self, state: QeuryingDatabaseState):
        """
        Decompose input statement into verifiable statement and analysis statement
        """
        query_model = (self.configurable_model
                       .with_config(self.deepseek_model_config)
                       .with_structured_output(PromptClarification))
        
        role = state.get("role", "")
        role_description = self.roles_config[role]["role_description"]

        full_prompt = clarification_prompt.format(
            role_description=role_description,
            natural_language_prompt=get_buffer_string(state.get("original_statement", "")),
        )
        response = query_model.ainvoke([HumanMessage(content=full_prompt)])

        return Command(
            goto="query_databases",
            update={
                "verifiable_prompt":response.verifiable_prompt,
                "analysis_statement": response.analysis_statement,
            }
        )

    async def query_databases(self, state: QeuryingDatabaseState, config: RunnableConfig, graph) -> Command[Literal[""]]:
        tools = [self.db_tools.execute_SQL_command, self.db_tools.execute_NoSQL_command]

        query_model = (self.configurable_model
                       .with_config(self.deepseek_model_config)
                       .with_structured_output(QueryDatabaseOutput)
                       .bind_tools(tools))
        
        """ history = list(graph.get_state_history(config))
        current_state = graph.get_state(config) """

        feedback = state.get("feedback", "")
        if len(feedback) > 0:
            feedback_string = ",".join(feedback)
        """ if len(history) > 1:
            if history[1].next == "query_result_feedback_generator":
                feedback = get_buffer_string(current_state.values.get("feedback")) """

        full_prompt = gen_query_prompt.format(
            verify_prompt=get_buffer_string(state.get("verifiable_prompt")),
            feedback=feedback_string,
            SQL_metadata=self.sql_db_metadata,
            NoSQL_metadata=self.nosql_db_metadata)  # ask for sql / nosql cmds, also executing the cmds

        response = query_model.ainvoke([HumanMessage(content=full_prompt)])

        tool_messages = [msg for msg in reversed(state["messages"]) 
                         if isinstance(msg, ToolMessage)]
        latest_tool_msg = tool_messages[0].content

        ai_messages = [msg for msg in reversed(state["messages"]) 
                         if isinstance(msg, AIMessage)]
        latest_ai_msg = ai_messages[0].content

        if isinstance(latest_tool_msg, str) and latest_tool_msg.split()[0] == "Error":
            if state.get("retry", 0) <= self.max_retry:
                return Command(
                    goto="query_result_feedback_generator",
                    update={    ### structured output
                        "query_code": response.get("query_code"),
                        "query_plan": response.get("query_plan"),
                        "error_message": latest_tool_msg,
                    }
                )
            else:
                return Command(goto=END,
                               update={
                                    "verification_decision": [False],
                                    "verification_result": [""],
                                    "failure_remarks": state["failure_remarks"].update(
                                        {f"{state.get("verifiable_prompt")}": "max retry exceeded"}
                                    )
                               })
        else:
            if latest_tool_msg != "" or latest_tool_msg is not None:
                if state.get("analysis_statement", None):
                    return Command(
                        goto="query_result_analysis",
                        update={
                            "query_result": latest_ai_msg,
                        })
                else:
                    return Command(goto=END, update={
                        "query_result": latest_ai_msg,
                        "verification_decision": [False],
                        "verification_result": [""],
                        "failure_remarks": state["failure_remarks"].update(
                            {f"{state.get("verifiable_prompt")}": "analysis statement missing"}
                        )
                    })
            else:
                return Command(goto=END,
                               update={
                                    "verification_decision": [False],
                                    "verification_result": [""],
                                    "failure_remarks": state["failure_remarks"].update(
                                        {f"{state.get("verifiable_prompt")}": "queried result not valid"}
                                    )
                               })    # todo- work out verification plan for user to do it themselves
            
    async def query_result_feedback_generator(self, state: QeuryingDatabaseState) -> Command[Literal[""]]:
        """
        Generate feedback to the query code generated in query_databases based on error message
        """
        gen_feedback_model = (self.configurable_model
                              .with_config(self.deepseek_model_config)
                              .with_structured_output(Feedback))

        assert (state.error_message is not None), \
            "if there is error arisen in query result, please provide error message"
        
        full_prompt = feedback_with_err_msg_prompt.format(
            verifiable_prompt=get_buffer_string(state.get("verifiable_prompt")), 
            query_plan=state.get("query_plan"), 
            query_code=state.get("query_code"), 
            error_message=state.get("error_message"))
        response = gen_feedback_model.ainvoke([HumanMessage(content=full_prompt)])

        return Command(
            goto="query_databases",
            update={
                "feedback": state.get("feedback", "").append(response.feedback),
                   "retry": state.get("retry", 0) + 1,   # from structured output
            }
        )            

    async def query_result_analysis(self, state: QeuryingDatabaseState):
        """
        Analyze the queried data if the query is successful and that the natural language prompt in prompt_clarification implies further interpretation on the queried data 
        """
        analysis_model = (self.configurable_model
                              .with_config(self.deepseek_model_config)
                              .with_structured_output(Analysis))

        full_prompt = analysis_prompt.format(
            natural_language_prompt=get_buffer_string(state.get("original_statement", "")),
            analysis_statement=get_buffer_string(state.get("analysis_statement")),
            query_result = state.get("query_result")
            ) 
        response = analysis_model.ainvoke([HumanMessage(content=full_prompt)])

        return Command(
            goto=END,
            update={
                "verification_decision": [response.get("verification_decision", True)],
                "verification_result": [response.get("verification_result", "")],
            }
        )
    
    async def aggregate_jobs(self, state: QeuryingDatabaseWrapperState):
        if False not in state.get("verification_decision"):
            return Command(
                goto=END,
                update={
                    "verification_decision": [True],
                    "verification_result": [""], # assume that no further notice or action if positive verification result
                })
        else:
            result_negative_verification = [result if decision is False else "" 
                                            for decision, result in zip(state["verification_decision"], state["verification_result"])]
            all_result_neg_ver = ""
            if len(result_negative_verification) > 0:
                all_result_neg_ver = ",".join(result_negative_verification)
            
            return Command(
                goto=END,
                update={
                    "verification_decision": [False],
                    "verification_result": [all_result_neg_ver],
                })

queryDatabase = QueryDatabases(max_retry=10)
query_db_builder = StateGraph(QeuryingDatabaseState)
query_db_builder.add_node("prompt_clarification", queryDatabase.promp_clarification)
query_db_builder.add_node("query_database", queryDatabase.query_databases)
query_db_builder.add_node("query_result_feedback_generator", queryDatabase.query_result_feedback_generator)
query_db_builder.add_node("query_result_analysis", queryDatabase.query_result_analysis)
# query_db_builder.add_edge(START, "prompt_clarification")
query_db_subgraph = query_db_builder.compile()

query_db_wrapper_builder = StateGraph(QeuryingDatabaseState)
query_db_wrapper_builder.add_node("job_assignment", queryDatabase.jobs_assignment)
query_db_wrapper_builder.add_node("query_database_subgraph", query_db_subgraph)
query_db_wrapper_builder.add_node("aggregate_jobs", queryDatabase.aggregate_jobs)
query_db_wrapper_builder.add_conditional_edges(
    source=START,
    path=queryDatabase.jobs_assignment,
    path_map=["query_database_subgraph"]
)
query_db_wrapper_builder.add_edge("query_database_subgraph", "aggregate_jobs")
query_db_wrapper = query_db_wrapper_builder.compile()