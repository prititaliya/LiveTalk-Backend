"""
Chatbot Agent Service

LangGraph agent for answering questions about transcripts with tools.
"""
import os
import logging
import json
from typing import List, Dict, Any, Annotated, Sequence, TypedDict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)

# Import calendar tools
try:
    from tools.calender import add_event, detect_followup_meetings, search_events, CalendarDate
except ImportError as e:
    logger.warning(f"Could not import calendar tools: {e}")
    add_event = None
    detect_followup_meetings = None
    search_events = None


# Define the state schema
class AgentState(TypedDict):
    """State for the chatbot agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    transcript_id: str
    retrieved_context: List[str]


# Define tools for the agent
@tool
def search_transcript(query: str, transcript_id: str, rag_service: Any) -> str:
    """
    Search the transcript for specific information.
    
    Args:
        query: The search query
        transcript_id: The meeting ID
        rag_service: RAG service instance
        
    Returns:
        Relevant transcript chunks as context
    """
    try:
        context = rag_service.get_transcript_context(transcript_id, query, k=5)
        if not context:
            return "No relevant information found in the transcript."
        return f"Relevant transcript excerpts:\n\n{context}"
    except Exception as e:
        logger.error(f"Error in search_transcript tool: {e}", exc_info=True)
        return f"Error searching transcript: {str(e)}"


@tool
def summarize_transcript(transcript_id: str, transcript_data: Dict) -> str:
    """
    Get a summary of the transcript.
    
    Args:
        transcript_id: The meeting ID
        transcript_data: Full transcript data
        
    Returns:
        Summary of the transcript
    """
    try:
        entries = transcript_data.get("transcripts", [])
        if not entries:
            return "The transcript is empty."
        
        total_entries = len(entries)
        speakers = set(entry.get("speaker", "Unknown") for entry in entries)
        meeting_name = transcript_data.get("meeting_name", "Unknown Meeting")
        start_time = transcript_data.get("start_time", "")
        
        summary = f"Meeting: {meeting_name}\n"
        summary += f"Total entries: {total_entries}\n"
        summary += f"Speakers: {', '.join(sorted(speakers))}\n"
        if start_time:
            summary += f"Started: {start_time}\n"
        
        # Get first and last few entries for context
        if entries:
            summary += f"\nFirst entry: {entries[0].get('speaker', 'Unknown')}: {entries[0].get('text', '')[:100]}...\n"
            if len(entries) > 1:
                summary += f"Last entry: {entries[-1].get('speaker', 'Unknown')}: {entries[-1].get('text', '')[:100]}...\n"
        
        return summary
    except Exception as e:
        logger.error(f"Error in summarize_transcript tool: {e}", exc_info=True)
        return f"Error summarizing transcript: {str(e)}"


@tool
def get_speaker_info(speaker_name: str, transcript_data: Dict) -> str:
    """
    Get information about a specific speaker in the transcript.
    
    Args:
        speaker_name: Name of the speaker
        transcript_data: Full transcript data
        
    Returns:
        Information about the speaker
    """
    try:
        entries = transcript_data.get("transcripts", [])
        speaker_entries = [e for e in entries if e.get("speaker", "").lower() == speaker_name.lower()]
        
        if not speaker_entries:
            return f"Speaker '{speaker_name}' not found in the transcript."
        
        total_entries = len(speaker_entries)
        total_words = sum(len(e.get("text", "").split()) for e in speaker_entries)
        
        # Get sample quotes
        sample_quotes = [e.get("text", "")[:150] for e in speaker_entries[:3]]
        
        info = f"Speaker: {speaker_name}\n"
        info += f"Total contributions: {total_entries}\n"
        info += f"Approximate word count: {total_words}\n"
        info += f"\nSample quotes:\n"
        for i, quote in enumerate(sample_quotes, 1):
            info += f"{i}. {quote}...\n"
        
        return info
    except Exception as e:
        logger.error(f"Error in get_speaker_info tool: {e}", exc_info=True)
        return f"Error getting speaker info: {str(e)}"


@tool
def extract_key_points(transcript_data: Dict) -> str:
    """
    Extract key discussion points from the transcript.
    
    Args:
        transcript_data: Full transcript data
        
    Returns:
        Key points extracted from the transcript
    """
    try:
        entries = transcript_data.get("transcripts", [])
        if not entries:
            return "The transcript is empty."
        
        # Simple extraction: look for questions, decisions, action items
        key_points = []
        
        for entry in entries:
            text = entry.get("text", "").lower()
            speaker = entry.get("speaker", "Unknown")
            
            # Look for questions
            if "?" in entry.get("text", ""):
                key_points.append(f"Question from {speaker}: {entry.get('text', '')[:200]}")
            
            # Look for decisions/agreements
            if any(word in text for word in ["decide", "decided", "agree", "agreed", "conclusion"]):
                key_points.append(f"Decision/Agreement: {entry.get('text', '')[:200]}")
            
            # Look for action items
            if any(word in text for word in ["will", "should", "need to", "must", "action"]):
                key_points.append(f"Action item: {entry.get('text', '')[:200]}")
        
        if not key_points:
            return "No specific key points identified. The transcript contains general discussion."
        
        return "Key Points:\n\n" + "\n\n".join(key_points[:10])  # Limit to 10 points
    except Exception as e:
        logger.error(f"Error in extract_key_points tool: {e}", exc_info=True)
        return f"Error extracting key points: {str(e)}"


class ChatbotAgent:
    """LangGraph agent for chatbot functionality"""
    
    def __init__(self, rag_service: Any, transcript_data: Dict, user_email: Optional[str] = None):
        """
        Initialize chatbot agent.
        
        Args:
            rag_service: RAG service instance
            transcript_data: Full transcript data
            user_email: User's email address for calendar operations (optional)
        """
        self.rag_service = rag_service
        self.transcript_data = transcript_data
        self.transcript_id = transcript_data.get("meeting_id", "")
        self.user_email = user_email
        
        # Initialize LLM
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        model_name = os.environ.get("CHATBOT_MODEL", "gpt-4o-mini")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.7,
            openai_api_key=openai_api_key,
            streaming=True
        )
        
        # Store references for tool functions
        self._rag_service = rag_service
        self._transcript_id = self.transcript_id
        self._transcript_data = transcript_data
        
        # Create tool functions that can access instance variables
        def search_transcript_wrapper(query: str) -> str:
            """Search the transcript for specific information."""
            return search_transcript.invoke({
                "query": query,
                "transcript_id": self._transcript_id,
                "rag_service": self._rag_service
            })
        
        def summarize_transcript_wrapper() -> str:
            """Get a summary of the transcript."""
            return summarize_transcript.invoke({
                "transcript_id": self._transcript_id,
                "transcript_data": self._transcript_data
            })
        
        def get_speaker_info_wrapper(speaker_name: str) -> str:
            """Get information about a specific speaker in the transcript."""
            return get_speaker_info.invoke({
                "speaker_name": speaker_name,
                "transcript_data": self._transcript_data
            })
        
        def extract_key_points_wrapper() -> str:
            """Extract key discussion points from the transcript."""
            return extract_key_points.invoke({
                "transcript_data": self._transcript_data
            })
        
        # Create tools from wrapper functions
        search_tool = tool(search_transcript_wrapper)
        summarize_tool = tool(summarize_transcript_wrapper)
        speaker_tool = tool(get_speaker_info_wrapper)
        key_points_tool = tool(extract_key_points_wrapper)
        
        # Store tools
        self.tools = [
            search_tool,
            summarize_tool,
            speaker_tool,
            key_points_tool,
        ]
        
        # Add calendar tools if available and user email is provided
        if self.user_email and add_event and detect_followup_meetings and search_events:
            # Create wrapper functions for calendar tools that include user email
            def add_event_wrapper(event_summary: str, date: Dict, location: str = "", reminder_before: int = 15, description: str = "") -> str:
                """Add an event to the user's calendar."""
                return add_event.invoke({
                    "event_summary": event_summary,
                    "date": date,
                    "email": self.user_email,
                    "location": location,
                    "reminder_before": reminder_before,
                    "description": description
                })
            
            def detect_followup_meetings_wrapper(transcript_text: str, current_date: Optional[str] = None) -> str:
                """Detect follow-up meetings from transcript text."""
                # Use full transcript if transcript_text is not provided or is short
                if not transcript_text or len(transcript_text) < 100:
                    # Build transcript text from transcript_data
                    entries = self._transcript_data.get("transcripts", [])
                    transcript_text = "\n".join([
                        f"{entry.get('speaker', 'Unknown')}: {entry.get('text', '')}"
                        for entry in entries
                    ])
                
                # Extract transcript start_time to use as reference date for relative date calculations
                transcript_start_date = None
                start_time = self._transcript_data.get("start_time")
                if start_time:
                    try:
                        # Parse the start_time (could be ISO format string or datetime)
                        if isinstance(start_time, str):
                            from datetime import datetime
                            # Try to parse ISO format
                            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            transcript_start_date = dt.strftime("%Y-%m-%d")
                        elif hasattr(start_time, 'strftime'):
                            transcript_start_date = start_time.strftime("%Y-%m-%d")
                    except Exception as e:
                        logger.warning(f"Could not parse transcript start_time: {e}")
                
                return detect_followup_meetings.invoke({
                    "transcript_text": transcript_text,
                    "transcript_start_date": transcript_start_date,
                    "current_date": current_date
                })
            
            def search_events_wrapper(query: str, max_results: int = 10) -> str:
                """Search the user's calendar for events."""
                return search_events.invoke({
                    "query": query,
                    "email": self.user_email,
                    "max_results": max_results
                })
            
            # Create tool wrappers
            add_event_tool = tool(add_event_wrapper)
            detect_followup_tool = tool(detect_followup_meetings_wrapper)
            search_events_tool = tool(search_events_wrapper)
            
            # Add calendar tools to tools list
            self.tools.extend([
                add_event_tool,
                detect_followup_tool,
                search_events_tool,
            ])
            
            logger.info(f"Calendar tools enabled for user: {self.user_email}")
        else:
            if not self.user_email:
                logger.info("Calendar tools disabled: user email not provided")
            else:
                logger.info("Calendar tools disabled: calendar tools not available")
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Create tool node
        self.tool_node = ToolNode(self.tools)
        
        # Build graph
        self.graph = self._build_graph()
        
        logger.info(f"Initialized ChatbotAgent for transcript {self.transcript_id}")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph"""
        
        def should_continue(state: Dict):
            """Determine if we should continue or end"""
            messages = state.get("messages", [])
            if not messages:
                return END
            
            last_message = messages[-1]
            
            # If there are tool calls, continue to tools
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            # Otherwise, end
            return END
        
        def call_model(state: Dict):
            """Call the LLM with conversation history"""
            messages = state.get("messages", [])
            
            # Add system message with context
            calendar_capability = ""
            if self.user_email and add_event:
                calendar_capability = """
You also have access to calendar tools:
- detect_followup_meetings: Analyze the transcript to find mentions of follow-up meetings or scheduled events
- add_event: Add events to the user's Google Calendar
- search_events: Search the user's calendar for existing events

When users mention follow-up meetings or ask about scheduling, use detect_followup_meetings first to extract meeting details.
Then, if the user wants to add the meeting to their calendar, use add_event. Always confirm with the user before adding events.
"""
            
            system_message = SystemMessage(
                content=f"""You are a helpful assistant that answers questions about meeting transcripts.
The transcript is from: {self.transcript_data.get('meeting_name', 'Unknown Meeting')}
You have access to tools to search, summarize, and extract information from the transcript.
Use these tools when needed to provide accurate answers.
Be concise but thorough in your responses.{calendar_capability}"""
            )
            
            # Combine system message with conversation
            full_messages = [system_message] + list(messages)
            
            response = self.llm_with_tools.invoke(full_messages)
            return {"messages": [response]}
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", self.tool_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        
        # Tools always return to agent
        workflow.add_edge("tools", "agent")
        
        # Compile graph
        return workflow.compile()
    
    async def process_message_async(self, user_message: str, conversation_history: List[Dict]) -> Any:
        """
        Process a user message and generate streaming response (async).
        
        Args:
            user_message: User's message
            conversation_history: Previous conversation messages
            
        Yields:
            Response chunks as they're generated
        """
        # Convert conversation history to LangChain messages
        messages = []
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current user message
        messages.append(HumanMessage(content=user_message))
        
        # Create initial state
        initial_state = {
            "messages": messages,
            "transcript_id": self.transcript_id,
            "retrieved_context": []
        }
        
        # Run graph and stream response
        config = {"configurable": {"thread_id": f"{self.transcript_id}"}}
        
        accumulated_content = ""
        last_yielded_length = 0
        
        # Stream the response
        async for chunk in self.graph.astream(initial_state, config):
            if "agent" in chunk:
                agent_messages = chunk["agent"]["messages"]
                for msg in agent_messages:
                    if isinstance(msg, AIMessage):
                        # Stream content incrementally
                        if msg.content:
                            # Only yield new content that hasn't been yielded yet
                            current_length = len(msg.content)
                            if current_length > last_yielded_length:
                                new_content = msg.content[last_yielded_length:]
                                last_yielded_length = current_length
                                accumulated_content = msg.content
                                yield new_content
            elif "tools" in chunk:
                # Tool execution - continue to next iteration
                continue
        
        # Final yield if there's any remaining content
        if accumulated_content and len(accumulated_content) > last_yielded_length:
            yield accumulated_content[last_yielded_length:]

