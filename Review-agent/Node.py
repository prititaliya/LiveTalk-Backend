from typing import Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import os
from ReviewState import ReviewState, Summary
from langchain_core.messages import HumanMessage, SystemMessage
from Tools import think_tool,tavily_search
class Node:
    def get_model(self, temperature: float = 0.0):
        return init_chat_model(
            model="gpt-5.4-mini",
            model_provider="openai",   
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        ).bind_tools([think_tool,tavily_search])

    def orchestratorAgent(self, state: ReviewState) -> ReviewState:
        if state["plan"] != "":
            state["iteration"] += 1
            return state
        system_message = SystemMessage(content="""You are the Manager of the code review process. Your job is to analyze the code changes and comments, and create a concise, actionable plan for the review process. 
        Rules for your plan:
        1. Be extremely brief and direct. Avoid generic boilerplate (e.g., "Step 1: Read the code").
        2. Limit the plan to 3 to 5 high-level bullet points.
        3. Focus only on what needs to be addressed based on the diff stats and user comments.
        4. If no user comments are provided, create a brief plan based purely on the diff stats.
        After executing the plan, analyze the results and determine in a single sentence if further iterations are necessary.""")
        human_message = HumanMessage(content=f"""Here is the current state of the review:
        - Diff Stats: {state['diff_stats']}
        - Code Comments: {state['code_comments']}
        - Summary: {state['summary']}
        - Plan: {state['plan']}
        - Action: {state['action']}
        - Result: {state['result']}
If you are unsure or need to reason about any part of the review, you MUST call the Think tool with a question and the current context before proceeding. Then, provide your concise, bulleted plan of action and next steps."""
        )

        class Plan(TypedDict):
                    plan: str

        gen_model = self.get_model(temperature=0.0).with_structured_output(Plan)
        response = gen_model.invoke([system_message, human_message])
        # Always set messages for tool node compatibility
        state["messages"] = [system_message, human_message]
        if hasattr(response, "tool_calls") and response.tool_calls:
            print("Tool calls detected in Orchestrator Agent response:", response.tool_calls)
            for tool_call in response.tool_calls:
                if tool_call["name"] == "SubmitPlan":
                    state["plan"] = tool_call["args"]["plan"]
                    print("Orchestrator Agent Plan Submitted:", state["plan"])
                elif tool_call["name"] == "Think":
                    print("Orchestrator is thinking...")
        print("Orchestrator Agent Response:", response)
        state["plan"] = response["plan"]
        print("Orchestrator Agent Response:", state["plan"])
        state["iteration"] += 1
        return state
    
    def fetch_prompt(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(base_dir, "prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def ReviewSubAgent1(self, state: ReviewState) -> ReviewState:
        system_message = SystemMessage(content=self.fetch_prompt())
        human_message = HumanMessage(
            content=f"""
            Your Goal is to work on the given Plan:
            {state['plan']}
             and execute it based on the given information about the code changes and comments:
            Diff Stats: {state['diff_stats']}
            Code Comments: {state['code_comments']}
            Code Diff: {state['full_diff']}
            suggestions for improvement based on the previous comments: {state['comments_review']}

            Based on this information, please create a concise summary of the code changes.
            **You MUST return all of the following fields in your response:**
            - summary: A plain English summary of the code changes and issues found.
            - result: A structured list of findings (bugs, vulnerabilities, etc).
            - result_markdown: A markdown-formatted version of the result for better readability (include code blocks, tables, etc).
            - code_suggestions: Suggestions for code improvement based on the previous comments.
            if you need more thoughts to make a decision, use the Think tool to think through the review process and gather your thoughts before creating the summary and results.
            Make sure to check the documentations from search tool if you need to find more information about any topic related to the review process.
            """
            )

        gen_model = self.get_model(temperature=0.0).with_structured_output(Summary)
        response = gen_model.invoke([system_message, human_message])
        # Always set messages for tool node compatibility
        state["messages"] = [system_message, human_message]
        if hasattr(response, "tool_calls") and response.tool_calls:
            print("Tool calls detected in ReviewSubAgent1 response:", response.tool_calls)
            for tool_call in response.tool_calls:
                if tool_call["name"] == "SubmitPlan":
                    state["plan"] = tool_call["args"]["plan"]
                    print("Orchestrator Agent Plan Submitted:", state["plan"])
                elif tool_call["name"] == "Think":
                    print("Orchestrator is thinking...")
                elif tool_call["name"] == "TavilySearch":
                    print("Orchestrator is searching the web...")
        print("Review SubAgent 1 Response:", response['summary'])
        state["summary"] = response["summary"]
        state["result"] = response["result"]
        state["markdown_summary"] = response["result_markdown"]
        state["comments_review"] = response["code_suggestions"]
        return state




    def conditional_node_to_end_or_review(self, state: ReviewState) -> ReviewState:
        print(f"""
        ========================================================
        Conditional Node Decision: next_step = {state["action"]}
        =======================================================""")
        if state["iteration"] >= 3:
            state["action"] = "end"
            return state

        if state["result"] == "":
            state["action"] = "review"
            return state

        system_message = SystemMessage(
            content="You are the decision maker for the code review process..."
        )
        human_message = HumanMessage(
            content=f"""Here is the information about the code review process:
            Plan: {state['plan']}
            Action: {state['action']}
            Result: {state['result']}

            Based on this information, decide whether to continue reviewing or end."""
            )

        class ReviewDecision(TypedDict):
            next_step: Literal["review", "end"]

        gen_model = self.get_model(temperature=0).with_structured_output(ReviewDecision)
        response = gen_model.invoke([system_message, human_message])
        state["action"] = response["next_step"]
      
        return state


    def check_comments_addressed(self, state: ReviewState) -> ReviewState:
        print("state in comment check node:", state)
        if len(state["code_comments"]) <= 0:
            return state

        comment_agent = self.get_model(temperature=0)
        system_message = SystemMessage(
            content=("""
                You are an agent that checks whether the code comments provided in the review process have been addressed in the code changes.
                Only Focus on the comments that are between <<COMMENT_START>> and <<COMMENT_END>> markers.
                For each comment, analyze the code changes to determine if the comment has been addressed.
                If a comment has been addressed, mark it as "Addressed". If it has not been addressed, mark it as "Not Addressed" and provide potential suggestions for improvement based on the comment."""
            )
        )
        human_message = HumanMessage(
            content=f"""
            Your goal is to analyze the code comments and the code changes to determine if the comments have been addressed.
            Here is the information about the code changes and comments:
            code_diff: {state['full_diff']}
            Code Comments: {state['code_comments']}
            Based on this information, determine if the comments have been addressed in the code changes. If not, flag that a review is needed and provide potential suggestions for improvement based on the comments.
            Give result in Markdown format for better readability."""
            )

        class CommentCheckResult(TypedDict):
            code_comments_review: str

        agent = comment_agent.with_structured_output(CommentCheckResult)
        response = agent.invoke([system_message, human_message])
        print("Comment Check Agent Response:", response)

        state["comments_review"] = response["code_comments_review"]
        return state


    def generate_summary(self, state: ReviewState) -> ReviewState:
        system_message = SystemMessage(
        content=(
            "You are an agent that generates a final in-depth analysis of the code review process, "
            "including the results and suggestions for improvement. "
            "You MUST include a section summarizing the review of PR comments (whether they were addressed or not), "
            "and do not miss any suggestion for improvement based on the comments. "
            "Also include a markdown formatted summary of the results for better readability."
        )
    )
        human_message = HumanMessage(
            content=f"""Here is the information about the code review process:
            Plan: {state['plan']}
            Action: {state['action']}
            Result: {state['result']}
            **PR Comments Review:** {state['comments_review']}
            Based on this information, generate a final summary of the code review process, including:
            - The results and suggestions for improvement.
            - A dedicated section for PR comments review (whether they were addressed or not, and any suggestions).
            - A markdown formatted summary of the results for better readability.
            """
                )

        class FinalSummary(TypedDict):
            final_summary: str

        gen_model = self.get_model(temperature=0).with_structured_output(FinalSummary)
        response = gen_model.invoke([system_message, human_message])
        state["markdown_summary"] = response["final_summary"]
        return state