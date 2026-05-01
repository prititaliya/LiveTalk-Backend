from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict
from ReviewState import ReviewState
from langchain.chat_models import init_chat_model
import os
from langchain_tavily import TavilySearch



def get_model(temperature: float = 0.0):
        return init_chat_model(
                model="gpt-5.4-mini",
                model_provider="openai",   
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY")
            )
@tool("Think")
def think_tool( question: str, context: str) -> str:
        """
        A tool for thinking through the review process.
        """
        system_message = SystemMessage(content="""
                                       You are a thoughtful assistant that helps analyze the code review process. Your job is to think through the current state of the review and provide insights and next steps based on the information provided. You are asked what thoughts they need to think through in order to make progress on the review process.""")
        human_message = HumanMessage(content=f"""Here is the context for your thoughts:
{context}

        Based on this information, provide your thoughts on what you need to think through in order to make progress on the review process. and Question  is {question}""") 

        class Plan(TypedDict):
            thoughts: str

        gen_model = get_model(temperature=0.0).with_structured_output(Plan)
        response = gen_model.invoke([system_message, human_message])
        print("Thinking...", response["thoughts"])

        return response["thoughts"]

@tool("TavilySearch")
def tavily_search(query: str) -> str:
    """
    A tool for searching the web using Tavily.
    """
    print(f"Searching the web for: {query}")
    tavily = TavilySearch()
    results = tavily.run(query)
    return results