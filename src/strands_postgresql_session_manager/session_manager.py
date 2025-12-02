"""
PostgreSQL Session Manager for Strands Agents SDK.

Provides persistent session storage using PostgreSQL with full ACID guarantees,
CASCADE deletes, and JSONB support for flexible state storage.
"""
import logging
from typing import Optional, List, Type
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from strands.session.repository_session_manager import RepositorySessionManager
from strands.session.session_repository import SessionRepository
from strands.types.session import (
    Session as StrandsSession,
    SessionAgent,
    SessionMessage,
    SessionType,
)

from .models import SessionDB, AgentDB, MessageDB


class PostgresSessionManager(RepositorySessionManager, SessionRepository):
    """
    PostgreSQL-based session manager with SQLModel persistence.
    
    Implements RepositorySessionManager and SessionRepository interfaces,
    acting as its own repository (similar to FileSessionManager pattern).
    
    This session manager provides:
    - Full ACID guarantees for all operations
    - CASCADE deletes for data integrity
    - JSONB storage for flexible state management
    - Synchronous operations (compatible with Celery and Strands SDK)
    
    Attributes:
        engine: SQLAlchemy sync engine for database connections
        SessionModel: SQLModel class for sessions table (default: SessionDB)
        AgentModel: SQLModel class for agents table (default: AgentDB)
        MessageModel: SQLModel class for messages table (default: MessageDB)
        logger: Logger instance for this session manager
    
    Example:
        >>> from sqlmodel import create_engine
        >>> from strands import Agent
        >>> from strands_postgresql_session_manager import PostgresSessionManager
        >>> 
        >>> # Create engine
        >>> engine = create_engine("postgresql://user:pass@localhost/db")
        >>> 
        >>> # Create session manager
        >>> session_manager = PostgresSessionManager(
        ...     session_id="user_123",
        ...     engine=engine
        ... )
        >>> 
        >>> # Use with Strands Agent
        >>> agent = Agent(session_manager=session_manager)
    """
    
    def __init__(
        self,
        session_id: str,
        engine: Engine,
        session_model: Type[SessionDB] = SessionDB,
        agent_model: Type[AgentDB] = AgentDB,
        message_model: Type[MessageDB] = MessageDB,
        logger: Optional[logging.Logger] = None,
        **kwargs
    ):
        """
        Initialize PostgresSessionManager.
        
        Args:
            session_id: Unique identifier for the session
            engine: SQLAlchemy sync engine for database connections
            session_model: SQLModel class for sessions (default: SessionDB)
            agent_model: SQLModel class for agents (default: AgentDB)
            message_model: SQLModel class for messages (default: MessageDB)
            logger: Custom logger instance (default: creates new logger)
            **kwargs: Additional arguments for future extensibility
        
        Note:
            The engine must be a synchronous SQLAlchemy engine, not async.
            Tables must be created before using the session manager.
        """
        # Store engine and models
        self.engine = engine
        self.SessionModel = session_model
        self.AgentModel = agent_model
        self.MessageModel = message_model
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize parent RepositorySessionManager
        super().__init__(session_id=session_id, session_repository=self)
        
        self.logger.debug(f"PostgresSessionManager initialized for session: {session_id}")
    
    # ==================== Session Methods ====================
    
    def create_session(self, session: StrandsSession, **kwargs) -> StrandsSession:
        """
        Create a new session in the database.
        
        Only creates if the session doesn't exist. If it already exists,
        returns the existing session without modification.
        
        Args:
            session: Strands Session object to create
            **kwargs: Additional arguments for future extensibility
        
        Returns:
            The created or existing Strands Session object
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                # Check if session already exists
                existing_session = db_session.get(self.SessionModel, session.session_id)
                
                if existing_session:
                    self.logger.debug(
                        f"Session {session.session_id} already exists, skipping creation"
                    )
                    return session
                
                # Get session data from Strands SDK
                session_data = session.to_dict()
                
                # Extract session_type (may be an Enum, need string value)
                session_type_value = session_data.get('session_type')
                if hasattr(session_type_value, 'value'):
                    session_type_value = session_type_value.value
                
                # Create SQLModel instance
                session_db = self.SessionModel(
                    session_id=session_data.get('session_id'),
                    session_type=session_type_value,
                    created_at=session_data.get('created_at'),
                    updated_at=session_data.get('updated_at'),
                )
                
                # Insert into database
                db_session.add(session_db)
                db_session.commit()
                
                self.logger.info(f"Session created: {session.session_id}")
                return session
                
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise
    
    def read_session(self, session_id: str, **kwargs) -> Optional[StrandsSession]:
        """
        Read a session from the database.
        
        Args:
            session_id: ID of the session to read
            **kwargs: Additional arguments for future extensibility
        
        Returns:
            Strands Session object if found, None otherwise
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = select(self.SessionModel).where(
                    self.SessionModel.session_id == session_id
                )
                result = db_session.exec(statement)
                session_db = result.one_or_none()
                
                if session_db:
                    session_data = session_db.model_dump()
                    
                    # Convert session_type string to SessionType enum
                    if 'session_type' in session_data and isinstance(
                        session_data['session_type'], str
                    ):
                        session_data['session_type'] = SessionType(session_data['session_type'])
                    
                    return StrandsSession.from_dict(session_data)
                return None
                
        except Exception as e:
            self.logger.error(f"Error reading session: {e}")
            raise
    
    def update_session(self, session: StrandsSession) -> StrandsSession:
        """
        Update an existing session in the database.
        
        Args:
            session: Strands Session object with updated data
        
        Returns:
            The updated Strands Session object
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = select(self.SessionModel).where(
                    self.SessionModel.session_id == session.session_id
                )
                result = db_session.exec(statement)
                session_db = result.one_or_none()
                
                if session_db:
                    # Session has minimal mutable fields
                    # updated_at is handled automatically by database
                    db_session.add(session_db)
                    db_session.commit()
                    db_session.refresh(session_db)
                    
                    self.logger.info(f"Session updated: {session.session_id}")
                else:
                    self.logger.warning(
                        f"Session {session.session_id} not found for update"
                    )
                
                return session
                
        except Exception as e:
            self.logger.error(f"Error updating session: {e}")
            raise
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all related data (CASCADE).
        
        This will automatically delete all associated agents and messages
        due to ON DELETE CASCADE foreign key constraints.
        
        Args:
            session_id: ID of the session to delete
        
        Returns:
            True if session was deleted, False if not found
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = select(self.SessionModel).where(
                    self.SessionModel.session_id == session_id
                )
                result = db_session.exec(statement)
                session_db = result.one_or_none()
                
                if session_db:
                    db_session.delete(session_db)
                    db_session.commit()
                    self.logger.info(f"Session deleted: {session_id}")
                    return True
                
                self.logger.warning(f"Session {session_id} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting session: {e}")
            raise
    
    # ==================== Agent Methods ====================
    
    def create_agent(self, session_id: str, session_agent: SessionAgent, **kwargs) -> None:
        """
        Create a new agent in the database.
        
        Args:
            session_id: ID of the parent session
            session_agent: Strands SessionAgent object to create
            **kwargs: Additional arguments for future extensibility
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                agent_data = session_agent.to_dict()
                
                # Create SQLModel with JSONB fields
                agent_db = self.AgentModel(
                    agent_id=agent_data.get('agent_id'),
                    session_id=session_id,
                    state=agent_data.get('state', {}),
                    conversation_manager_state=agent_data.get('conversation_manager_state', {}),
                    internal_state=agent_data.get('_internal_state', {}),
                    created_at=agent_data.get('created_at'),
                    updated_at=agent_data.get('updated_at')
                )
                
                db_session.add(agent_db)
                db_session.commit()
                
                self.logger.info(f"Agent created: {session_agent.agent_id}")
                
        except Exception as e:
            self.logger.error(f"Error creating agent: {e}")
            raise
    
    def read_agent(self, session_id: str, agent_id: str, **kwargs) -> Optional[SessionAgent]:
        """
        Read an agent from the database.
        
        Args:
            session_id: ID of the parent session
            agent_id: ID of the agent to read
            **kwargs: Additional arguments for future extensibility
        
        Returns:
            Strands SessionAgent object if found, None otherwise
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = (
                    select(self.AgentModel)
                    .where(self.AgentModel.agent_id == agent_id)
                    .where(self.AgentModel.session_id == session_id)
                )
                result = db_session.exec(statement)
                agent_db = result.one_or_none()
                
                if agent_db:
                    agent_data = agent_db.model_dump()
                    # Map internal_state → _internal_state for SDK
                    agent_data['_internal_state'] = agent_data.pop('internal_state', {})
                    
                    return SessionAgent.from_dict(agent_data)
                return None
                
        except Exception as e:
            self.logger.error(f"Error reading agent: {e}")
            raise
    
    def update_agent(self, session_id: str, session_agent: SessionAgent, **kwargs) -> None:
        """
        Update an existing agent in the database.
        
        Args:
            session_id: ID of the parent session
            session_agent: Strands SessionAgent object with updated data
            **kwargs: Additional arguments for future extensibility
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = (
                    select(self.AgentModel)
                    .where(self.AgentModel.agent_id == session_agent.agent_id)
                    .where(self.AgentModel.session_id == session_id)
                )
                result = db_session.exec(statement)
                agent_db = result.one_or_none()
                
                if agent_db:
                    agent_data = session_agent.to_dict()
                    
                    # Update JSONB fields
                    agent_db.state = agent_data.get('state', {})
                    agent_db.conversation_manager_state = agent_data.get(
                        'conversation_manager_state', {}
                    )
                    agent_db.internal_state = agent_data.get('_internal_state', {})
                    agent_db.updated_at = agent_data.get('updated_at')
                    
                    db_session.add(agent_db)
                    db_session.commit()
                    
                    self.logger.info(f"Agent updated: {agent_data.get('agent_id')}")
                else:
                    self.logger.warning(
                        f"Agent {session_agent.agent_id} not found for update"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error updating agent: {e}")
            raise
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent from the database.
        
        Args:
            agent_id: ID of the agent to delete
        
        Returns:
            True if agent was deleted, False if not found
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = select(self.AgentModel).where(
                    self.AgentModel.agent_id == agent_id
                )
                result = db_session.exec(statement)
                agent_db = result.one_or_none()
                
                if agent_db:
                    db_session.delete(agent_db)
                    db_session.commit()
                    self.logger.info(f"Agent deleted: {agent_id}")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting agent: {e}")
            raise
    
    def list_agents(self, session_id: str) -> List[SessionAgent]:
        """
        List all agents for a session.
        
        Args:
            session_id: ID of the parent session
        
        Returns:
            List of Strands SessionAgent objects
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = (
                    select(self.AgentModel)
                    .where(self.AgentModel.session_id == session_id)
                    .order_by(self.AgentModel.created_at)
                )
                result = db_session.exec(statement)
                agents_db = result.all()
                
                agents = []
                for agent_db in agents_db:
                    agent_data = agent_db.model_dump()
                    # Map internal_state → _internal_state for SDK
                    agent_data['_internal_state'] = agent_data.pop('internal_state', {})
                    agents.append(SessionAgent.from_dict(agent_data))
                
                return agents
                
        except Exception as e:
            self.logger.error(f"Error listing agents: {e}")
            raise
    
    # ==================== Message Methods ====================
    
    def create_message(
        self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs
    ) -> None:
        """
        Create a new message in the database.
        
        Args:
            session_id: ID of the parent session
            agent_id: ID of the parent agent
            session_message: Strands SessionMessage object to create
            **kwargs: Additional arguments for future extensibility
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                message_data = session_message.to_dict()
                
                # Create SQLModel with JSONB fields
                message_db = self.MessageModel(
                    message_id=message_data.get('message_id'),
                    session_id=session_id,
                    agent_id=agent_id,
                    message=message_data.get('message'),
                    redact_message=message_data.get('redact_message'),
                    created_at=message_data.get('created_at'),
                    updated_at=message_data.get('updated_at'),
                )
                
                db_session.add(message_db)
                db_session.commit()
                
                self.logger.debug(f"Message created: {session_message.message_id}")
                
        except Exception as e:
            self.logger.error(f"Error creating message: {e}")
            raise
    
    def read_message(
        self, session_id: str, agent_id: str, message_id: int, **kwargs
    ) -> Optional[SessionMessage]:
        """
        Read a message from the database.
        
        Args:
            session_id: ID of the parent session
            agent_id: ID of the parent agent
            message_id: ID of the message to read
            **kwargs: Additional arguments for future extensibility
        
        Returns:
            Strands SessionMessage object if found, None otherwise
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = (
                    select(self.MessageModel)
                    .where(self.MessageModel.message_id == message_id)
                    .where(self.MessageModel.session_id == session_id)
                    .where(self.MessageModel.agent_id == agent_id)
                )
                result = db_session.exec(statement)
                message_db = result.one_or_none()
                
                if message_db:
                    message_data = message_db.model_dump()
                    return SessionMessage.from_dict(message_data)
                return None
                
        except Exception as e:
            self.logger.error(f"Error reading message: {e}")
            raise
    
    def update_message(
        self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs
    ) -> None:
        """
        Update an existing message in the database.
        
        Args:
            session_id: ID of the parent session
            agent_id: ID of the parent agent
            session_message: Strands SessionMessage object with updated data
            **kwargs: Additional arguments for future extensibility
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = (
                    select(self.MessageModel)
                    .where(self.MessageModel.message_id == session_message.message_id)
                    .where(self.MessageModel.session_id == session_id)
                    .where(self.MessageModel.agent_id == agent_id)
                )
                result = db_session.exec(statement)
                message_db = result.one_or_none()
                
                if message_db:
                    message_data = session_message.to_dict()
                    
                    # Update JSONB fields
                    message_db.message = message_data.get('message')
                    message_db.redact_message = message_data.get('redact_message')
                    message_db.updated_at = message_data.get('updated_at')
                    
                    db_session.add(message_db)
                    db_session.commit()
                    
                    self.logger.debug(f"Message updated: {session_message.message_id}")
                else:
                    self.logger.warning(
                        f"Message {session_message.message_id} not found for update"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error updating message: {e}")
            raise
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message from the database.
        
        Args:
            message_id: ID of the message to delete
        
        Returns:
            True if message was deleted, False if not found
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = select(self.MessageModel).where(
                    self.MessageModel.message_id == message_id
                )
                result = db_session.exec(statement)
                message_db = result.one_or_none()
                
                if message_db:
                    db_session.delete(message_db)
                    db_session.commit()
                    self.logger.debug(f"Message deleted: {message_id}")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting message: {e}")
            raise
    
    def list_messages(
        self,
        session_id: str,
        agent_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        **kwargs
    ) -> List[SessionMessage]:
        """
        List messages for a session and agent with pagination.
        
        Args:
            session_id: ID of the parent session
            agent_id: ID of the parent agent
            limit: Maximum number of messages to return (None = all)
            offset: Number of messages to skip
            **kwargs: Additional arguments for future extensibility
        
        Returns:
            List of Strands SessionMessage objects
        
        Raises:
            Exception: If database operation fails
        """
        try:
            with Session(self.engine) as db_session:
                statement = (
                    select(self.MessageModel)
                    .where(self.MessageModel.session_id == session_id)
                    .where(self.MessageModel.agent_id == agent_id)
                    .order_by(self.MessageModel.message_id)
                )
                
                # Apply pagination
                if offset:
                    statement = statement.offset(offset)
                if limit:
                    statement = statement.limit(limit)
                
                result = db_session.exec(statement)
                messages_db = result.all()
                
                # Convert to SessionMessage
                messages = []
                for message_db in messages_db:
                    message_data = message_db.model_dump()
                    messages.append(SessionMessage.from_dict(message_data))
                
                return messages
                
        except Exception as e:
            self.logger.error(f"Error listing messages: {e}")
            raise
