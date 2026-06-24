from ..agent.config.model_config import DeepSeekConfig
from ..tools.general import GeneralTools
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.types import Command
from langgraph.graph import HumanMessage
from langchain_core.messages import MessageLikeRepresentation
from ..agent.prompts.system_prompts import plotting_prompt

class DataVisualizationTools():
    def __init__(self):
        self.configurable_model = init_chat_model(configurable_fields=("model", "max_tokens", 
                                                                       "temperature", "api_key"))
        '''self.model_config = {
            "model": DeepSeekConfig.model,
            "max_tokens": DeepSeekConfig.max_tokens,
            "temperature": DeepSeekConfig.temperature,
            "api_key": DeepSeekConfig.api_key,
        }''' # search for another multimodal model supporting multimodal payload in output messages

    @tool
    async def plotting(self, messages:list[MessageLikeRepresentation], query_result: str):
        tools = [GeneralTools.code_executor]
        query_model = (self.configurable_model
                       .with_config(self.model_config)
                       .with_structured_output()
                       .bind_tools(tools))

        human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        system_prompt = plotting_prompt.format(human_messages, query_result)  # get instruction for graph plotting from full human messages context
        response = query_model.ainvoke()

        return ""