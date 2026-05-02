import base64
import json

from chromadb import QueryResult
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage,ToolMessage,AIMessage
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
class SearchResult(TypedDict):
        original_query: str
        previous_tried_queries: List[str]
        results: List[str]
        flag: bool
@tool
def cross_repository_search(query: str,full_state: ReviewState) -> str:
    """
    A tool for performing cross-repository search to find relevant information about potential breaking changes and their impact on the current Frontend codebase.
    If there is any API change that can potentially impact the frontend codebase, it should be detected by this tool and the search results should be analyzed to provide insights on the potential impact and suggestions for improvement if needed.
    """
    print(f"Performing cross-repository search with query: {query}")
    depenedent_repo = os.getenv("DEPENDENT_REPO")
    if not depenedent_repo:
        return "No dependent repository specified. Please set the DEPENDENT_REPO environment variable to perform cross-repository search. Right now we can not be sure if it would break the frontend or not, so we will assume it does break the frontend. Please set the DEPENDENT_REPO environment variable to perform cross-repository search and get more accurate results."
    
    shell_tool = ShellTool()

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
             it would become "gh search code /ws/transcripts/ --repo {depenedent_repo}"
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
            make_a_patch(search_results, full_state)
            return "‼️‼️‼️‼️THERE IS BREAKING CHANGE WITH POTENTIAL IMPACT ON FRONTEND, WHICH WOULD IMPACT THE FRONTEND AT: " + str(response["results"])
    return "NO BREAKING CHANGE DETECTED WITH POTENTIAL IMPACT ON FRONTEND. SEARCH RESULTS: " + str(response["results"])



def make_a_patch(search_results: str, state: ReviewState):
    repo_name = os.getenv("DEPENDENT_REPO")
    file_name = search_results.split(":")[1]  # Assuming the file name is the first word in the search results
    print(f"Making a patch for file: {file_name} in repository: {repo_name} based on search results: {search_results}")

    repoSHA_command = f"gh api repos/{repo_name}/git/ref/heads/main"
    print(f"Fetching latest commit SHA for repository {repo_name} using command: {repoSHA_command}")
    shell_tool = ShellTool()
    object_SHa = shell_tool.run({"commands": [repoSHA_command]})
    repoSHA= json.loads(object_SHa)["object"]["sha"]
    print(f"Latest commit SHA for repository {repo_name}: {repoSHA}")

    file_command = f"gh api repos/{repo_name}/contents/{file_name}?ref={repoSHA}"
    print(f"Fetching file content for {file_name} using command: {file_command}")
    file_content_response = shell_tool.run({"commands": [file_command]})
    file_content = json.loads(file_content_response)["content"]
    # base 64 decode the file content
    file_content = base64.b64decode(file_content).decode("utf-8")

    system_prompt = SystemMessage(content=f"""
        You are a helpful assistant that creates a patch for the given file based on the search results indicating a potential breaking change with impact on the frontend. Your task is to analyze the search results, understand the potential breaking change, and generate a patch for the file that addresses the issue.
        Here are the search results indicating the potential breaking change: {search_results}
        Here is the current content of the file: {file_content}
        Based on this information, create a patch that addresses the potential breaking change and ensures compatibility with the frontend. The patch should be in unified diff format and should clearly indicate the changes made to the file.
    """)
    human_msg = HumanMessage(content=f"""
        Please generate a patch for the file {file_name} based on the search results and the current file content. The patch should address the potential breaking change and ensure compatibility with the frontend. Please provide the patch in unified diff format.
        I am also providing you the current state of the review process to help you understand the context better: {state}
    """)

    gen_model = init_chat_model(    
                model="gpt-5.4-mini",
                model_provider="openai",   
                temperature=0.0,
                api_key=os.getenv("OPENAI_API_KEY")
            )   
    response = gen_model.invoke([system_prompt, human_msg])
    new_branch = f"""
                    gh api \
                --method POST \
                -H "Accept: application/vnd.github+json" \
                "repos/{repo_name}/git/refs" \
                -f ref="refs/heads/fix/{file_name}" \
                -f sha="{repoSHA}" """
    print(f"Creating a new branch for the patch using command: {new_branch}")
    shell_tool.run({"commands": [new_branch]})
    print("checking out the new branch...")
    shell_tool.run({"commands": [f"git checkout fix/{file_name}"]})
    print("Applying the patch...")
    patch_command = f"echo '{response}' | git apply --unidiff-zero --unsafe-paths"
    print(f"Applying the patch using command: {patch_command}")
    shell_tool.run({"commands": [patch_command]})
    print("Committing the changes...")
    commit_command = f"git commit -am 'Fixing potential breaking change in {file_name} based on search results'"
    print(f"Committing the changes using command: {commit_command}")
    shell_tool.run({"commands": [commit_command]})
    print("Pushing the changes to the new branch...")
    push_command = f"git push origin fix/{file_name}"
    print(f"Pushing the changes using command: {push_command}")
    shell_tool.run({"commands": [push_command]})
    print(f"Patch for {file_name} has been created and pushed to the new branch fix/{file_name}. Please review the changes and create a pull request to merge the patch into the main branch.")
    print(f"creating a pull request for the patch...")
    pr_command = f"""gh pr create --title "Fixing potential breaking change in {file_name}" --body "This pull request addresses a potential breaking change in {file_name} based on the search results indicating a potential impact on the frontend. Please review the changes and merge if everything looks good." --head fix/{file_name} --base main"""
    print(f"Creating a pull request using command: {pr_command}")
    shell_tool.run({"commands": [pr_command]})

    
with open("final_state.txt", 'r') as f:
    state = f.read()
make_a_patch("prititaliya/LiveTalk-Fronend:Frontend/components/RecordingControls.tsx: const ws = new WebSocket(`${wsUrl}/ws/transcripts/${room}`);", state)