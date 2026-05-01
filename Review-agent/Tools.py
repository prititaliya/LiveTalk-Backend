from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage,ToolMessage
from typing import TypedDict
from ReviewState import ReviewState
from langchain.chat_models import init_chat_model
import os
from langchain_tavily import TavilySearch
from langchain_community.tools import ShellTool
from langgraph.graph.message import add_messages
from typing import TypedDict, List

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
def get_model(temperature: float = 0.0):
        return init_chat_model(
                model="gpt-5.4-mini",
                model_provider="openai",   
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY")
            )
@tool
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

@tool
def tavily_search(query: str) -> str:
    """
    A tool for searching the web using Tavily.
    """
    print(f"Searching the web for: {query}")
    tavily = TavilySearch()
    results = tavily.run(query)
    return str(results)

@tool
def cross_repository_search(query: str) -> str:
    """
    A tool for performing cross-repository search to find relevant information about potential breaking changes and their impact on the current Frontend codebase.
    If there is any API change that can potentially impact the frontend codebase, it should be detected by this tool and the search results should be analyzed to provide insights on the potential impact and suggestions for improvement if needed.
    """
    print(f"Performing cross-repository search with query: {query}")
    shell_tool = ShellTool()
    print(shell_tool.run({"commands": ["gh search code /ws/transcripts/ --repo prititaliya/LiveTalk-Fronend", "time"]}))
    class SearchResult(TypedDict):
        original_query: str
        previous_tried_queries: List[str]
        results: List[str]
        flag: bool
    class QueryResult(TypedDict):
        query: str
    state= SearchResult(
        original_query=query,
        previous_tried_queries=[],
        results=[],
        flag=False
    )
    for i in range(3):  # Try up to 3 times
        print(f"Attempt {i+1} for cross-repository search...")
        system_message = SystemMessage(content=f"""
            You are a helpful assistant that performs cross-repository searches to find relevant information about potential breaking changes and their impact on the current Frontend codebase. Your task is to analyze the given query, generate search queries, and execute them to gather information that can help assess the impact of the change.
            """)
        human_message = HumanMessage(content=f"""
            Here is the original query: {query}
            Based on this query, generate a search query that can be used to find relevant information across repositories. If you have already tried some queries, consider them and generate a new one if necessary.
            {{"previous_tried_queries": {state['previous_tried_queries']}, "results": {state['results']}}}
             If you find information that indicates a potential breaking change with impact on the frontend, set the flag to True. Otherwise, keep it False.
             and reposetory is prititaliya/LiveTalk-Fronend, so that should be the suffix for example
             for query "/ws/transcripts/"
             it would become "gh search code /ws/transcripts/ --repo prititaliya/LiveTalk-Fronend"
            """)
        gen_model = init_chat_model(
                model="gpt-5.4-mini",
                model_provider="openai",   
                temperature=0.0,
                api_key=os.getenv("OPENAI_API_KEY")
            ).with_structured_output(QueryResult)
        response = gen_model.invoke([system_message, human_message])
        print("Generated search query:", response)
        print("Generated search query:", response["query"])
        
        
        try:
            search_results = shell_tool.run({"commands": [response["query"]]})
        except Exception as e:
            search_results = f"search error: {e}"
        print("Search results:", search_results)
        state["previous_tried_queries"] = state.get("previous_tried_queries", []) + [response["query"]]
        state["results"] = state.get("results", []) + [str(search_results)]
        response["results"] = response.get("results", []) + [str(search_results)]

        if search_results:
                return "THERE IS BREAKING CHANGE WITH POTENTIAL IMPACT ON FRONTEND. SEARCH RESULTS: " + str(search_results)  
    if state["flag"]:
      return "THERE IS BREAKING CHANGE WITH POTENTIAL IMPACT ON FRONTEND. SEARCH RESULTS: " + str(response["results"])
    else:
         return "NO BREAKING CHANGE DETECTED WITH POTENTIAL IMPACT ON FRONTEND. SEARCH RESULTS: " + str(response["results"])

