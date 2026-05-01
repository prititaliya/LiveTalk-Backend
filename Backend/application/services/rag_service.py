"""
RAG Service

Handles Retrieval Augmented Generation for transcripts:
- Chunking transcripts into manageable pieces
- Generating embeddings
- Storing and retrieving relevant chunks
"""
import os
import logging
from typing import List, Dict, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma, InMemoryVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG operations on transcripts"""
    
    def __init__(self):
        """Initialize RAG service with embeddings and vector store"""
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        self.vector_store_type = os.environ.get("VECTOR_STORE_TYPE", "memory").lower()
        
        # Initialize embeddings
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            openai_api_key=openai_api_key
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=self._count_tokens,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Vector stores per transcript (in-memory for now)
        self._vector_stores: Dict[str, InMemoryVectorStore] = {}
        
        logger.info(f"Initialized RAGService with model: {self.embedding_model}, store_type: {self.vector_store_type}")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        try:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            return len(encoding.encode(text))
        except:
            # Fallback to character count / 4 (rough estimate)
            return len(text) // 4
    
    def _create_chunks_from_transcript(self, transcript_data: Dict) -> List[Document]:
        """
        Create document chunks from transcript data.
        
        Args:
            transcript_data: Dictionary containing transcript data
            
        Returns:
            List of Document objects with metadata
        """
        chunks = []
        transcript_entries = transcript_data.get("transcripts", [])
        
        # Group entries by speaker turns for better context
        current_speaker = None
        current_text_parts = []
        current_timestamps = []
        
        for entry in transcript_entries:
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            timestamp = entry.get("timestamp", "")
            
            if not text.strip():
                continue
            
            # If same speaker, accumulate text
            if speaker == current_speaker:
                current_text_parts.append(text)
                if timestamp:
                    current_timestamps.append(timestamp)
            else:
                # Save previous speaker's chunk
                if current_speaker and current_text_parts:
                    chunk_text = f"{current_speaker}: {' '.join(current_text_parts)}"
                    metadata = {
                        "speaker": current_speaker,
                        "timestamps": current_timestamps,
                        "meeting_id": transcript_data.get("meeting_id", ""),
                        "meeting_name": transcript_data.get("meeting_name", ""),
                    }
                    chunks.append(Document(page_content=chunk_text, metadata=metadata))
                
                # Start new speaker chunk
                current_speaker = speaker
                current_text_parts = [text]
                current_timestamps = [timestamp] if timestamp else []
        
        # Don't forget the last chunk
        if current_speaker and current_text_parts:
            chunk_text = f"{current_speaker}: {' '.join(current_text_parts)}"
            metadata = {
                "speaker": current_speaker,
                "timestamps": current_timestamps,
                "meeting_id": transcript_data.get("meeting_id", ""),
                "meeting_name": transcript_data.get("meeting_name", ""),
            }
            chunks.append(Document(page_content=chunk_text, metadata=metadata))
        
        # Further split large chunks if needed
        all_chunks = []
        for chunk in chunks:
            split_chunks = self.text_splitter.split_documents([chunk])
            all_chunks.extend(split_chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks from transcript {transcript_data.get('meeting_id')}")
        return all_chunks
    
    def index_transcript(self, transcript_data: Dict) -> None:
        """
        Index a transcript by creating chunks and storing embeddings.
        
        Args:
            transcript_data: Dictionary containing transcript data
        """
        meeting_id = transcript_data.get("meeting_id")
        if not meeting_id:
            raise ValueError("Transcript data must include meeting_id")
        
        try:
            # Create chunks
            chunks = self._create_chunks_from_transcript(transcript_data)
            
            if not chunks:
                logger.warning(f"No chunks created for transcript {meeting_id}")
                return
            
            # Create vector store for this transcript
            if self.vector_store_type == "memory":
                vector_store = InMemoryVectorStore(self.embeddings)
                vector_store.add_documents(chunks)
                self._vector_stores[meeting_id] = vector_store
            else:
                # For ChromaDB, use persistent storage
                persist_directory = f"./vectorstores/{meeting_id}"
                vector_store = Chroma.from_documents(
                    documents=chunks,
                    embedding=self.embeddings,
                    persist_directory=persist_directory
                )
                self._vector_stores[meeting_id] = vector_store
            
            logger.info(f"Indexed transcript {meeting_id} with {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Error indexing transcript {meeting_id}: {e}", exc_info=True)
            raise
    
    def retrieve_relevant_chunks(self, meeting_id: str, query: str, k: int = 5) -> List[Dict]:
        """
        Retrieve relevant chunks from a transcript based on query.
        
        Args:
            meeting_id: The meeting ID
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            List of dictionaries with chunk content and metadata
        """
        if meeting_id not in self._vector_stores:
            logger.warning(f"Transcript {meeting_id} not indexed, attempting to load from storage")
            # Try to load transcript and index it
            from lib.transcript_storage import get_transcript
            transcript_data = get_transcript(meeting_id)
            if transcript_data:
                self.index_transcript(transcript_data)
            else:
                return []
        
        vector_store = self._vector_stores.get(meeting_id)
        if not vector_store:
            logger.error(f"Vector store not found for transcript {meeting_id}")
            return []
        
        try:
            # Perform similarity search
            docs = vector_store.similarity_search(query, k=k)
            
            # Format results
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
            
            logger.info(f"Retrieved {len(results)} relevant chunks for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error retrieving chunks for transcript {meeting_id}: {e}", exc_info=True)
            return []
    
    def get_transcript_context(self, meeting_id: str, query: str, k: int = 5) -> str:
        """
        Get formatted context string from relevant chunks.
        
        Args:
            meeting_id: The meeting ID
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            Formatted context string
        """
        chunks = self.retrieve_relevant_chunks(meeting_id, query, k)
        
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk["content"]
            metadata = chunk.get("metadata", {})
            speaker = metadata.get("speaker", "Unknown")
            
            context_parts.append(f"[Chunk {i}] {content}")
        
        return "\n\n".join(context_parts)
    
    def clear_index(self, meeting_id: str) -> None:
        """Clear the index for a specific transcript"""
        if meeting_id in self._vector_stores:
            del self._vector_stores[meeting_id]
            logger.info(f"Cleared index for transcript {meeting_id}")

