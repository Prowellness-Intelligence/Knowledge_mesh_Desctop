# Knowledge Mesh Desktop API Documentation

This document describes the API for the Knowledge Mesh Desktop application, including the core components, services, models, and UI components.

## Core Components

### Application Core (app.py)

The Application class is the main entry point for the application. It manages the application lifecycle, initializes services, and coordinates communication between components.

```python
class Application:
    def __init__(self, config_dir: Optional[str] = None)
    async def initialize_services()
    async def start_services()
    async def initialize_ui()
    async def start_ui()
    async def run()
    async def shutdown()
```

### Configuration System (config.py)

The Config class provides methods for loading, accessing, and modifying configuration settings.

```python
class Config:
    def __init__(self, config_dir: Optional[str] = None)
    def get(self, key: str, default: Any = None) -> Any
    def set(self, key: str, value: Any)
    def update(self, values: Dict[str, Any])
    def reset()
    def get_all() -> Dict[str, Any]
```

### Event Bus (events.py)

The event bus facilitates communication between components through events.

```python
class EventType(Enum):
    # Application events
    APP_STARTED = auto()
    APP_STOPPING = auto()
    
    # Configuration events
    CONFIG_CHANGED = auto()
    
    # File events
    FILE_DETECTED = auto()
    FILE_PROCESSED = auto()
    
    # Document events
    DOCUMENT_CREATED = auto()
    DOCUMENT_UPDATED = auto()
    DOCUMENT_DELETED = auto()
    DOCUMENT_PROCESSED = auto()
    
    # Relationship events
    RELATIONSHIP_DISCOVERED = auto()
    RELATIONSHIP_CREATED = auto()
    RELATIONSHIP_UPDATED = auto()
    RELATIONSHIP_DELETED = auto()
    
    # UI events
    OPEN_DOCUMENT = auto()
    OPEN_RELATIONSHIP = auto()
    PERFORM_ACTION = auto()
    
    # Proactive events
    WORK_PATTERN_DETECTED = auto()
    PROACTIVE_INTERACTION = auto()

class Event:
    def __init__(self, type: EventType, data: Dict[str, Any] = None)

def publish(event_type: EventType, data: Dict[str, Any] = None)
def subscribe(event_type: EventType, callback: Callable[[Event], None])
def unsubscribe(event_type: EventType, callback: Callable[[Event], None])
```

## Models

### Document Model (document.py)

The Document class represents a document in the knowledge mesh.

```python
class DocumentType(Enum):
    PDF = auto()
    DOCX = auto()
    TXT = auto()
    MARKDOWN = auto()
    CSV = auto()
    EXCEL = auto()
    IMAGE = auto()
    EMAIL = auto()
    CALENDAR = auto()
    WEBPAGE = auto()
    UNKNOWN = auto()

class DocumentStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    PROCESSED = auto()
    FAILED = auto()
    DELETED = auto()

class Document:
    def __init__(
        self,
        id: str,
        title: str,
        content: str,
        file_path: Optional[str] = None,
        file_type: Optional[DocumentType] = None,
        embedding: Optional[np.ndarray] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: DocumentStatus = DocumentStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    )
    
    @property
    def filename(self) -> Optional[str]
    @property
    def extension(self) -> Optional[str]
    @property
    def size(self) -> Optional[int]
    @property
    def word_count(self) -> int
    @property
    def is_processed(self) -> bool
    
    def add_chunk(self, chunk: "DocumentChunk")
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document"

class DocumentChunk:
    def __init__(
        self,
        id: str,
        document_id: str,
        content: str,
        embedding: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_index: int = 0,
    )
    
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk"
```

### Relationship Model (relationship.py)

The Relationship class represents a relationship between documents in the knowledge mesh.

```python
class RelationshipType(Enum):
    SEMANTIC_SIMILARITY = auto()
    KEYWORD_OVERLAP = auto()
    REFERENCE_LINK = auto()
    TEMPORAL_PROXIMITY = auto()
    AUTHOR_SIMILARITY = auto()
    TOPIC_SIMILARITY = auto()
    PARENT_CHILD = auto()
    DERIVED_FROM = auto()
    RELATED_TO = auto()
    CUSTOM = auto()

class RelationshipStrength(Enum):
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4

class Relationship:
    def __init__(
        self,
        source_id: str,
        target_id: str,
        type: RelationshipType,
        strength: float,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    )
    
    @property
    def strength_category(self) -> RelationshipStrength
    @property
    def is_bidirectional(self) -> bool
    
    def to_dict(self) -> Dict[str, Any]
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship"
```

## Services

### File Monitor Service (file_monitor.py)

The FileMonitorService monitors the file system for new documents.

```python
class FileMonitorService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def restart()
    def register_handler(self, extension: str, handler: Callable[[str], Awaitable[None]])
    def unregister_handler(self, extension: str)
```

### Document Processor Service (document_processor.py)

The DocumentProcessorService extracts text and metadata from documents.

```python
class DocumentProcessorService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def process_document(self, file_path: str) -> Optional[Document]
    async def extract_text(self, file_path: str) -> Tuple[str, Dict[str, Any]]
    async def generate_summary(self, text: str) -> str
    async def chunk_document(self, document: Document) -> List[DocumentChunk]
```

### Vector Store Service (vector_store.py)

The VectorStoreService indexes document content for semantic search.

```python
class VectorStoreService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def add_document(self, document: Document)
    async def add_chunk(self, chunk: DocumentChunk)
    async def search(self, query: str, limit: int = 10) -> List[Tuple[str, float]]
    async def delete_document(self, document_id: str)
```

### Knowledge Mesh Service (knowledge_mesh.py)

The KnowledgeMeshService discovers and manages relationships between documents.

```python
class KnowledgeMeshService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def discover_relationships(self, document: Document)
    async def create_relationship(self, source_id: str, target_id: str, type: RelationshipType, strength: float, metadata: Dict[str, Any] = None)
    async def get_relationships(self, document_id: str) -> List[Relationship]
    async def delete_relationship(self, source_id: str, target_id: str)
```

### Proactive Service (proactive_service.py)

The ProactiveService provides suggestions and insights based on user behavior.

```python
class UserState(Enum):
    UNKNOWN = auto()
    FOCUSED = auto()
    INTERRUPTIBLE = auto()
    IDLE = auto()
    AWAY = auto()

class ProactiveService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def track_interaction(self, interaction_type: str, data: Dict[str, Any] = None)
    async def detect_user_state() -> UserState
    async def generate_suggestion() -> Dict[str, Any]
```

### Calendar Service (calendar_service.py)

The CalendarService integrates with calendar applications.

```python
class CalendarService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def sync_calendars()
    async def get_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]
    async def find_related_documents(self, event: Dict[str, Any]) -> List[Document]
```

### Email Service (email_service.py)

The EmailService processes emails and attachments.

```python
class EmailService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def sync_emails()
    async def get_emails(self, limit: int = 100) -> List[Dict[str, Any]]
    async def process_attachment(self, attachment: Dict[str, Any]) -> Optional[Document]
```

### Voice Service (voice_service.py)

The VoiceService enables voice interaction with the application.

```python
class VoiceService:
    def __init__(self, config: Config)
    async def initialize()
    async def start()
    async def stop()
    async def listen() -> str
    async def speak(text: str)
    async def process_command(command: str) -> Dict[str, Any]
```

## UI Components

### Main Window (main_window.py)

The MainWindow is the main application window.

```python
class MainWindow:
    def __init__(self, config: Config, services: Dict[str, Any])
    async def initialize()
    async def start()
    async def stop()
    def show()
    def hide()
```

### Document Panel (document_panel.py)

The DocumentPanel displays and manages documents.

```python
class DocumentPanel:
    def __init__(self, parent, config: Config, services: Dict[str, Any])
    async def initialize()
    async def start()
    async def stop()
    def refresh()
    def show_document(self, document_id: str)
```

### Relationship Panel (relationship_panel.py)

The RelationshipPanel displays and manages relationships.

```python
class RelationshipPanel:
    def __init__(self, parent, config: Config, services: Dict[str, Any])
    async def initialize()
    async def start()
    async def stop()
    def refresh()
    def show_relationship(self, relationship_id: str)
```

### Search Panel (search_panel.py)

The SearchPanel enables semantic search across documents and relationships.

```python
class SearchPanel:
    def __init__(self, parent, config: Config, services: Dict[str, Any])
    async def initialize()
    async def start()
    async def stop()
    def refresh()
    def search(self, query: str, search_type: str = "all")
```

### Settings Panel (settings_panel.py)

The SettingsPanel configures application settings.

```python
class SettingsPanel:
    def __init__(self, parent, config: Config, services: Dict[str, Any])
    async def initialize()
    async def start()
    async def stop()
    def refresh()
    def save_settings()
    def reset_settings()
```

### Notification Panel (notification_panel.py)

The NotificationPanel displays proactive notifications.

```python
class NotificationPanel:
    def __init__(self, parent, config: Config, services: Dict[str, Any])
    async def initialize()
    async def start()
    async def stop()
    def show()
    def hide()
    def show_notification(self, interaction_type: str, content: Dict[str, Any])
```

## Event Handling

Components communicate through events using the event bus. Here are some common event flows:

### Document Discovery Flow

1. File Monitor Service detects a new document
2. `FILE_DETECTED` event is published
3. Document Processor Service processes the document
4. `DOCUMENT_PROCESSED` event is published
5. Vector Store Service indexes the document
6. Knowledge Mesh Service discovers relationships
7. `RELATIONSHIP_DISCOVERED` event is published
8. UI Components update to show the new document and relationships

### Proactive Assistance Flow

1. Proactive Service monitors user behavior
2. Work pattern is detected
3. `WORK_PATTERN_DETECTED` event is published
4. Proactive Service generates a suggestion
5. `PROACTIVE_INTERACTION` event is published
6. Notification Panel displays the suggestion

### User Interaction Flow

1. User interacts with the UI
2. UI Component publishes an event (e.g., `OPEN_DOCUMENT`)
3. Relevant Service handles the event
4. Service publishes a response event
5. UI Components update based on the response

## Configuration

The configuration system allows for customization of all aspects of the system. The configuration is stored in a JSON file and can be modified through the Settings Panel or by editing the file directly. Here are some common configuration keys:

### File Monitor Configuration

```json
{
  "file_monitor": {
    "directories": ["~/Documents", "~/Downloads"],
    "extensions": [".pdf", ".docx", ".txt", ".md"],
    "recursive": true,
    "ignore_patterns": [".*", "~*", "Thumbs.db", "desktop.ini"],
    "polling_interval": 5,
    "enabled": true
  }
}
```

### Document Processor Configuration

```json
{
  "document_processor": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "extract_metadata": true,
    "generate_summaries": true,
    "summary_length": 200,
    "ocr_enabled": true,
    "ocr_language": "eng",
    "max_workers": 4
  }
}
```

### Knowledge Mesh Configuration

```json
{
  "knowledge_mesh": {
    "embedding_model": "all-MiniLM-L6-v2",
    "similarity_threshold": 0.7,
    "min_strength": 0.3,
    "auto_detect": true,
    "relationship_types": [
      "SEMANTIC_SIMILARITY",
      "KEYWORD_OVERLAP",
      "TEMPORAL_PROXIMITY"
    ],
    "max_relationships": 50
  }
}
```

### Proactive Configuration

```json
{
  "proactive": {
    "enabled": true,
    "min_interaction_interval": 15,
    "max_daily_interactions": 20,
    "interaction_types": [
      "DOCUMENT_SUGGESTION",
      "RELATIONSHIP_SUGGESTION",
      "WORK_PATTERN_INSIGHT"
    ],
    "work_pattern_learning": true,
    "privacy_level": "MEDIUM",
    "notification_style": "STANDARD",
    "notification_timeout": 10
  }
}
```

## Extending the Application

The application is designed to be easily extended with new features and capabilities:

### Adding a New Service

To add a new service to the application:

1. Create a new file in the `src/services` directory
2. Define a class that implements the service interface
3. Register the service in the application core
4. Subscribe to relevant events

Example:

```python
from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

class MyService:
    def __init__(self, config: Config):
        self.config = config
        self.is_running = False
        
    async def initialize(self):
        # Initialize the service
        pass
        
    async def start(self):
        # Start the service
        self.is_running = True
        
    async def stop(self):
        # Stop the service
        self.is_running = False
        
    def _on_event(self, event):
        # Handle events
        pass
```

### Adding a New UI Component

To add a new UI component to the application:

1. Create a new file in the `src/ui` directory
2. Define a class that implements the UI component interface
3. Add the component to the main window
4. Subscribe to relevant events

Example:

```python
import tkinter as tk
from tkinter import ttk
from ..core.config import Config
from ..core.events import EventType, publish, subscribe, event_bus

class MyComponent:
    def __init__(self, parent, config: Config, services: Dict[str, Any]):
        self.parent = parent
        self.config = config
        self.services = services
        self.frame = None
        
    async def initialize(self):
        # Initialize the component
        self.frame = ttk.Frame(self.parent)
        
    async def start(self):
        # Start the component
        pass
        
    async def stop(self):
        # Stop the component
        pass
        
    def refresh(self):
        # Refresh the component
        pass
```

### Adding a New Document Type

To add support for a new document type:

1. Add the new document type to the `DocumentType` enum
2. Implement a new method in the `DocumentProcessorService` to extract text from the new document type
3. Register a handler for the new document type in the `FileMonitorService`

Example:

```python
# Add to DocumentType enum
class DocumentType(Enum):
    # ...
    MY_TYPE = auto()

# Add to DocumentProcessorService
async def extract_my_type_text(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
    # Extract text and metadata from the file
    # ...
    return text, metadata

# Register handler in FileMonitorService
service.register_handler(".mytype", document_processor.process_document)
```

### Adding a New Relationship Type

To add a new relationship type:

1. Add the new relationship type to the `RelationshipType` enum
2. Implement a new method in the `KnowledgeMeshService` to discover the new relationship type
3. Update the configuration to include the new relationship type

Example:

```python
# Add to RelationshipType enum
class RelationshipType(Enum):
    # ...
    MY_RELATIONSHIP = auto()

# Add to KnowledgeMeshService
async def discover_my_relationship(self, document: Document) -> List[Relationship]:
    # Discover relationships of the new type
    # ...
    return relationships

# Update configuration
config.set("knowledge_mesh.relationship_types", [
    # ...
    "MY_RELATIONSHIP"
])
```
