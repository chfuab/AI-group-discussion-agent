from pydantic import BaseModel, Field
from langchain_deepseek import ChatDeepSeek
from langchain.chat_models import init_chat_model
import os

class DeepSeekConfig(BaseModel):
    model:str = "deepseek-chat"
    default:str = "deepseek-chat"
    temperature:float = 0.7
    max_tokens:int = None
    timeout:int = 60
    max_retries:int = 3
    api_key=""
      