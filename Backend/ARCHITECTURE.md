# LiveTalk Backend Architecture

## Overview

LiveTalk is a real-time transcription and speaker diarization system built with **5-tier architecture** following **SOLID principles**. The system uses LiveKit for real-time audio processing, Speechmatics for speech-to-text with native speaker diarization, and Redis/PostgreSQL for data persistence.

## System Components

### Core Technologies
- **LiveKit**: Real-time audio/video streaming and agent framework
- **Speechmatics**: Primary STT provider with native speaker diarization
- **FastAPI**: REST API framework
- **Redis**: Transcript caching and real-time storage
- **PostgreSQL**: User authentication and persistent data storage
- **OpenAI**: Chatbot and RAG (Retrieval Augmented Generation) capabilities

## Architecture Layers

### 1. Presentation Layer (`presentation/`)
**Purpose**: Handles HTTP requests, WebSocket connections, and LiveKit agent entry points

**Components**:
- **API Routes** (`presentation/api/routes/`):
  - `health_routes.py`: Health check endpoints
  - `token_routes.py`: LiveKit token generation
  - `transcript_routes.py`: Transcript retrieval and management
  - `auth_routes.py`: User authentication (login/register)
  - `chatbot_routes.py`: AI chatbot endpoints with RAG
- **WebSocket** (`presentation/websocket/`):
  - Real-time transcript updates to frontend
- **DTOs** (`presentation/dto/`):
  - Request/response data transfer objects
- **Middleware** (`presentation/middleware/`):
  - CORS, authentication, error handling
- **Agents** (`presentation/agents/`):
  - LiveKit agent implementations (currently in `main.py`)

**Entry Points**:
- `api.py`: FastAPI application server
- `main.py`: LiveKit transcription agent (DiarizationAgent)

### 2. Application Layer (`application/`)
**Purpose**: Contains business logic, services, and use cases

**Services** (`application/services/`):
- **`transcript_service.py`**: Transcript business logic and orchestration
- **`speaker_service.py`**: Speaker management and labeling
- **`speaker_diarization_service.py`**: Speaker diarization logic (native vs manual)
- **`auth_service.py`**: User authentication logic
- **`jwt_service.py`**: JWT token generation and validation
- **`rag_service.py`**: Retrieval Augmented Generation for chatbot
- **`chatbot_agent.py`**: AI chatbot agent with LangGraph
- **`conversation_memory.py`**: Conversation history management

**Use Cases** (`application/use_cases/`):
- `generate_token.py`: Generate LiveKit access tokens
- `save_transcript.py`: Save transcripts to storage
- `get_transcript.py`: Retrieve transcripts
- `register_user.py`: User registration
- `login_user.py`: User authentication

### 3. Domain Layer (`domain/`)
**Purpose**: Core business entities, value objects, and interfaces

**Components**:
- **Entities** (`domain/entities/`):
  - `user.py`: User domain model
  - `transcript.py`: Transcript domain model
  - `speaker.py`: Speaker domain model
  - `meeting.py`: Meeting domain model
- **Interfaces** (`domain/interfaces/`):
  - `stt_service.py`: STT provider abstraction
  - `transcript_repository.py`: Transcript storage abstraction
  - `user_repository.py`: User storage abstraction
  - `file_storage.py`: File storage abstraction
  - `livekit_service.py`: LiveKit service abstraction
- **Value Objects** (`domain/value_objects/`):
  - Domain-specific value objects

### 4. Data Access Layer (`data_access/`)
**Purpose**: Repository pattern and data mappers

**Components**:
- **Repositories** (`data_access/repositories/`):
  - `transcript_repository.py`: Transcript repository interface
  - `user_repository.py`: User repository interface
- **Mappers** (`data_access/mappers/`):
  - `transcript_mapper.py`: Transcript entity mapping
  - `user_mapper.py`: User entity mapping

### 5. Infrastructure Layer (`infrastructure/`)
**Purpose**: External services and infrastructure implementations

**Components**:
- **Repository Implementations** (`infrastructure/repositories/`):
  - `redis_transcript_repository.py`: Redis-based transcript storage
  - `postgres_user_repository.py`: PostgreSQL-based user storage
- **Service Implementations** (`infrastructure/services/`):
  - **`unified_stt_service.py`**: Unified STT service supporting multiple providers
    - Speechmatics (default, with native diarization)
    - Deepgram (manual diarization)
    - AssemblyAI (manual diarization)
  - **`livekit_service.py`**: LiveKit API client for token generation and RTMP ingress
- **Storage** (`infrastructure/storage/`):
  - `file_storage.py`: Local file system storage
- **Configuration** (`infrastructure/config/`):
  - `redis_config.py`: Redis connection configuration
  - `database.py`: PostgreSQL database configuration

### Core Layer (`core/`)
**Purpose**: Dependency injection, configuration, and shared utilities

**Components**:
- **`dependency_injection.py`**: DI container managing all dependencies
- **`config.py`**: Application configuration
- **`exceptions.py`**: Custom exception classes

## STT Provider Architecture

### Unified STT Service
The system uses a **UnifiedSTTService** that abstracts multiple STT providers:

1. **Speechmatics** (Default, Recommended)
   - Native speaker diarization support
   - Configured with `max_speakers=10`
   - Automatic speaker detection and labeling
   - Set via `STT_MODEL=speechmatics` (default)

2. **Deepgram** (Alternative)
   - Manual diarization via turn detection
   - Set via `STT_MODEL=deepgram`

3. **AssemblyAI** (Alternative)
   - Manual diarization via turn detection
   - Set via `STT_MODEL=assemblyai`

### Speaker Diarization

**Native Diarization (Speechmatics)**:
- Speechmatics API provides speaker IDs automatically
- System extracts speaker information from multiple attributes:
  - `speaker_id`, `speaker`, `speaker_label` from alternatives
  - Event-level speaker attributes
  - Dictionary inspection for additional fields
- Trusts API results without manual intervention

**Manual Diarization (Deepgram/AssemblyAI)**:
- Uses turn detection and pause analysis
- Detects speaker changes based on:
  - Significant pauses (>1.5 seconds)
  - Turn detection signals
  - Audio characteristics changes

## Data Flow

### Transcription Flow
```
RTMP Stream → LiveKit Room → DiarizationAgent → UnifiedSTTService → Speechmatics API
                                                                         ↓
                                                              Speaker IDs + Transcript
                                                                         ↓
                                                              SpeakerDiarizationService
                                                                         ↓
                                                              TranscriptService
                                                                         ↓
                                                              Redis + File Storage
```

### API Request Flow
```
HTTP Request → FastAPI Router → Use Case → Service → Repository → Infrastructure
                                                                         ↓
                                                              Database/Redis/Storage
```

## SOLID Principles Applied

### Single Responsibility Principle (SRP)
- Each service has one clear purpose:
  - `TranscriptService`: Transcript business logic
  - `SpeakerDiarizationService`: Diarization logic only
  - `UnifiedSTTService`: STT provider abstraction
  - `AuthService`: Authentication logic

### Open/Closed Principle (OCP)
- STT providers can be added without modifying existing code
- New repository implementations extend interfaces
- Services are extensible via interfaces

### Liskov Substitution Principle (LSP)
- Repository implementations are interchangeable
- STT providers follow `ISTTService` interface
- All implementations follow their interface contracts

### Interface Segregation Principle (ISP)
- Small, focused interfaces:
  - `ISTTService`: STT operations only
  - `ITranscriptRepository`: Transcript operations only
  - `IFileStorage`: File operations only

### Dependency Inversion Principle (DIP)
- High-level modules depend on abstractions (interfaces)
- `DIContainer` manages all dependencies
- Services depend on interfaces, not implementations

## Key Design Patterns

1. **Repository Pattern**: Abstracts data access
   - `ITranscriptRepository` → `RedisTranscriptRepository`
   - `IUserRepository` → `PostgresUserRepository`

2. **Strategy Pattern**: STT provider selection
   - `UnifiedSTTService` selects provider based on `STT_MODEL` env var

3. **Dependency Injection**: Loose coupling
   - `DIContainer` manages all dependencies
   - Services receive dependencies via constructor

4. **Use Case Pattern**: Encapsulates business operations
   - Each use case represents a single business operation
   - Clear input/output contracts

5. **DTO Pattern**: Separates API contracts from domain models
   - Request/response DTOs in `presentation/dto/`

## File Structure

```
Backend/
├── core/                           # Dependency injection, config
│   ├── dependency_injection.py    # DI container
│   ├── config.py                  # App configuration
│   └── exceptions.py              # Custom exceptions
│
├── domain/                         # Domain layer
│   ├── entities/                   # Domain entities
│   ├── interfaces/                 # Service/repository interfaces
│   └── value_objects/              # Value objects
│
├── infrastructure/                 # Infrastructure implementations
│   ├── repositories/               # Repository implementations
│   ├── services/                   # External service implementations
│   │   ├── unified_stt_service.py  # STT provider abstraction
│   │   └── livekit_service.py      # LiveKit API client
│   ├── storage/                    # Storage implementations
│   └── config/                     # Infrastructure config
│
├── data_access/                    # Data access layer
│   ├── repositories/               # Repository interfaces
│   └── mappers/                    # Entity mappers
│
├── application/                    # Application layer
│   ├── services/                   # Business logic services
│   │   ├── transcript_service.py
│   │   ├── speaker_diarization_service.py
│   │   ├── auth_service.py
│   │   └── rag_service.py
│   └── use_cases/                  # Use cases
│
├── presentation/                    # Presentation layer
│   ├── api/routes/                 # API route handlers
│   ├── websocket/                  # WebSocket handlers
│   ├── dto/                        # Data transfer objects
│   ├── middleware/                 # Middleware
│   └── agents/                     # LiveKit agents
│
├── api.py                          # FastAPI application entry point
├── main.py                         # LiveKit agent entry point (DiarizationAgent)
├── requirements.txt                # Python dependencies
└── env.example                     # Environment variables template
```

## Configuration

### Environment Variables

**STT Configuration**:
- `STT_MODEL`: STT provider (`speechmatics`, `deepgram`, `assemblyai`)
- `SPEECHMATICS_API_KEY`: Speechmatics API key (required for default)
- `DEEPGRAM_API_KEY`: Deepgram API key (if using Deepgram)
- `ASSEMBLYAI_API_KEY`: AssemblyAI API key (if using AssemblyAI)

**LiveKit Configuration**:
- `LIVEKIT_URL`: LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret

**Database Configuration**:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_HOST`, `REDIS_PORT`: Redis configuration

**Other**:
- `OPENAI_API_KEY`: OpenAI API key for chatbot
- `JWT_SECRET_KEY`: JWT signing secret

## Benefits

1. **Testability**: Each layer can be tested independently
   - Mock interfaces for unit testing
   - Integration tests for each layer

2. **Maintainability**: Clear separation of concerns
   - Easy to locate code
   - Changes isolated to specific layers

3. **Extensibility**: Easy to add new features
   - Add new STT providers via `UnifiedSTTService`
   - Add new repositories via interfaces
   - Add new use cases without modifying existing code

4. **Flexibility**: Can swap implementations
   - Switch STT providers via environment variable
   - Replace Redis with another cache
   - Swap file storage with cloud storage

5. **SOLID Compliance**: Follows all SOLID principles
   - Single responsibility per class
   - Open for extension, closed for modification
   - Liskov substitution for all implementations
   - Interface segregation for focused contracts
   - Dependency inversion throughout

## Current Features

✅ Real-time transcription with speaker diarization  
✅ Multiple STT provider support (Speechmatics, Deepgram, AssemblyAI)  
✅ Native speaker diarization via Speechmatics  
✅ RTMP stream ingestion  
✅ WebSocket real-time transcript updates  
✅ User authentication (JWT)  
✅ AI chatbot with RAG  
✅ Transcript storage (Redis + File system)  
✅ RESTful API  

## Future Enhancements

- [ ] Add more STT providers
- [ ] Cloud storage integration (S3, GCS)
- [ ] Advanced speaker identification
- [ ] Real-time translation
- [ ] Video transcription
- [ ] Analytics and reporting
