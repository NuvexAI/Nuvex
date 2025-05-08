import uuid
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import Column, String, Boolean, DateTime, func, JSON, Text, LargeBinary, BigInteger, Integer, \
    ForeignKey, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from agents.models.base import Base


class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="Name of the category")
    type = Column(String(50), nullable=False, comment="Type of the category: agent or tool")
    description = Column(Text, comment="Description of the category")
    tenant_id = Column(String(255), comment="Tenant ID")
    sort_order = Column(Integer, default=0, comment="Sort order for display")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")


class App(Base):
    __tablename__ = 'app'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()).replace('-', ''), comment="UUID ID")
    name = Column(String(255), nullable=False, comment="Name of the app")
    description = Column(Text, comment="Description of the app")
    mode = Column(String(50), default='ReAct', comment="Mode of the app: function call, ReAct (default)")
    icon = Column(String(255), comment="Icon URL of the app")
    status = Column(String(50), comment="Status of the app: draft, active, inactive")
    role_settings = Column(Text, comment="Role settings for the agent")
    welcome_message = Column(Text, comment="Welcome message for the agent")
    twitter_link = Column(String(255), comment="Twitter link for the agent")
    telegram_bot_id = Column(String(255), comment="Telegram bot ID for the agent")
    telegram_bot_name = Column(String(255), comment="Telegram bot name")
    telegram_bot_token = Column(String(1000), comment="Encrypted Telegram bot token")
    token = Column(String(255), comment="Token symbol for the agent")
    symbol = Column(String(50), comment="Symbol for the agent token")
    photos = Column(JSON, comment="Photos for the agent")
    demo_video = Column(String(255), comment="Demo video URL for the agent")
    tool_prompt = Column(Text, comment="Tool prompt for the agent")
    max_loops = Column(Integer, default=3, comment="Maximum number of loops the agent can perform")
    model_json = Column(JSON, comment="Additional fields merged into a JSON column")
    custom_config = Column(JSON, comment="Custom configuration for the agent stored as JSON")
    tenant_id = Column(String(255), default=None, comment="Tenant ID")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    is_public = Column(Boolean, default=False, comment="Whether the agent is public")
    is_official = Column(Boolean, default=False, comment="Whether the agent is official preset")
    is_hot = Column(Boolean, default=False, comment="Whether the agent is hot")
    create_fee = Column(Numeric(20, 9), default=0.000000000, comment="Fee for creating the agent (tips for creator)")
    price = Column(Numeric(20, 9), default=0.000000000, comment="Fee for using the agent")
    vip_level = Column(Integer, default=0, comment="VIP level required to access this agent")
    tools = relationship('Tool', secondary='agent_tools', backref='agents')
    suggested_questions = Column(JSON, comment="List of suggested questions for the agent")
    model_id = Column(BigInteger, ForeignKey('models.id'), comment="ID of the associated model")
    category_id = Column(BigInteger, ForeignKey('categories.id'), comment="ID of the category")
    model = relationship('Model')
    category = relationship('Category')
    dev = Column(String(255), comment="Developer wallet address")
    enable_mcp = Column(Boolean, default=False, comment="Whether MCP is enabled for this agent")


class Tool(Base):
    __tablename__ = 'tools'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="UUID")
    name = Column(String(255), nullable=False)
    description = Column(String(800), nullable=True, comment="Description of the tool")
    type = Column(String(50), nullable=False)
    # OpenAPI specific fields
    origin = Column(String(255), comment="API origin")
    path = Column(String(255), comment="API path")
    method = Column(String(20), comment="HTTP method")
    parameters = Column(JSON, comment="API parameters including header, query, path, and body")
    # Common fields
    auth_config = Column(JSON)
    icon = Column(String(255), comment="Icon URL of the tool")
    is_deleted = Column(Boolean, default=False)
    tenant_id = Column(String(36))
    is_public = Column(Boolean, default=False)
    is_official = Column(Boolean, default=False)
    is_stream = Column(Boolean, default=False, comment="Whether the API returns a stream response")
    output_format = Column(JSON, comment="JSON configuration for formatting API output")
    sensitive_data_config = Column(JSON, comment="Configuration for sensitive data handling")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category_id = Column(BigInteger, ForeignKey('categories.id'), comment="ID of the category")
    category = relationship('Category')


class FileStorage(Base):
    __tablename__ = 'file_storage'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="Auto-incrementing ID")
    file_name = Column(String(255), nullable=False, comment="Name of the file")
    file_uuid = Column(String(255), nullable=False, comment="file UUID")
    file_content = Column(LargeBinary, nullable=True, comment="Content of the file (null for S3 storage)")
    size = Column(BigInteger, nullable=False, comment="Size of the file")
    storage_type = Column(String(50), default="database", comment="Storage type: database or s3")
    storage_location = Column(String(1000), nullable=True, comment="Storage location for external storage")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(120), unique=True, nullable=False)
    email = Column(String(120), unique=True)
    password = Column(String(255))
    wallet_address = Column(String(42), unique=True)
    chain_type = Column(String(20), default="ethereum", comment="Blockchain type, e.g., 'ethereum' or 'solana'")
    nonce = Column(String(32))
    tenant_id = Column(String(255))
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    open_platform_keys = relationship("OpenPlatformKey", back_populates="user")
    vip_memberships = relationship("VipMembership", back_populates="user")

    def set_password(self, password):
        """Set password."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Check password."""
        try:
            return check_password_hash(self.password, password)
        except Exception:
            pass
        return False

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'wallet_address': self.wallet_address,
            'chain_type': self.chain_type,
            'email': self.email
        }


class AgentTool(Base):
    __tablename__ = 'agent_tools'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column(String(36), ForeignKey('app.id', ondelete='CASCADE'), nullable=False)
    tool_id = Column(String(36), ForeignKey('tools.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(String(255), comment="Tenant ID")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")


class Model(Base):
    __tablename__ = 'models'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="Name of the model")
    model_name = Column(String(255), nullable=False, comment="Name of the underlying model (e.g. gpt-4, claude-3)")
    endpoint = Column(String(255), nullable=False, comment="API endpoint of the model")
    api_key = Column(String(1000), comment="API key for the model")
    is_official = Column(Boolean, default=False, comment="Whether the model is official preset")
    is_public = Column(Boolean, default=False, comment="Whether the model is public")
    icon = Column(String(255), comment="Icon URL of the model")
    tenant_id = Column(String(255), comment="Tenant ID")
    create_time = Column(DateTime, server_default=func.now(), comment="Creation time")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Last update time")


class OpenPlatformKey(Base):
    __tablename__ = "open_platform_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    access_key = Column(String(255), unique=True, nullable=False)
    secret_key = Column(String(255), nullable=False)
    token = Column(String(1000), nullable=True)
    token_created_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="open_platform_keys")


# Add MCP related models
class MCPServer(Base):
    """MCP Server model for storing MCP server configurations"""
    __tablename__ = "mcp_server"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(36), nullable=False)
    create_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    update_time = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tools = relationship("MCPTool", back_populates="mcp_server", cascade="all, delete-orphan")
    prompts = relationship("MCPPrompt", back_populates="mcp_server", cascade="all, delete-orphan")
    resources = relationship("MCPResource", back_populates="mcp_server", cascade="all, delete-orphan")


class MCPTool(Base):
    """Association between MCP servers and tools"""
    __tablename__ = "mcp_tool"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mcp_server_id = Column(Integer, ForeignKey("mcp_server.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(String(36), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False)
    create_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    mcp_server = relationship("MCPServer", back_populates="tools")
    tool = relationship("Tool")
    
    __table_args__ = (
        UniqueConstraint('mcp_server_id', 'tool_id', name='uq_mcp_tool'),
    )


class MCPPrompt(Base):
    """MCP Prompt template model"""
    __tablename__ = "mcp_prompt"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mcp_server_id = Column(Integer, ForeignKey("mcp_server.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    arguments = Column(JSON, nullable=True)
    template = Column(Text, nullable=False)
    create_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    update_time = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    mcp_server = relationship("MCPServer", back_populates="prompts")
    
    __table_args__ = (
        UniqueConstraint('mcp_server_id', 'name', name='uq_mcp_prompt_name'),
    )


class MCPResource(Base):
    """MCP Resource model"""
    __tablename__ = "mcp_resource"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mcp_server_id = Column(Integer, ForeignKey("mcp_server.id", ondelete="CASCADE"), nullable=False)
    uri = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    mime_type = Column(String(100), nullable=False, default="text/plain")
    create_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    update_time = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    mcp_server = relationship("MCPServer", back_populates="resources")
    
    __table_args__ = (
        UniqueConstraint('mcp_server_id', 'uri', name='uq_mcp_resource_uri'),
    )


class VipMembership(Base):
    """Membership table"""
    __tablename__ = "vip_memberships"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="User ID")
    level = Column(Integer, default=1, comment="Membership level")
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow, comment="Membership start time")
    expire_time = Column(DateTime, nullable=False, comment="Membership expiration time")
    status = Column(String(20), default="active", comment="Membership status: active, expired, cancelled")
    create_time = Column(DateTime, default=datetime.utcnow, comment="Creation time")
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Update time")
    
    # Relationships
    user = relationship("User", back_populates="vip_memberships")
    
    __table_args__ = (
        Index("idx_vip_memberships_user_status", "user_id", "status"),
    )


class VipPackage(Base):
    """Membership package table"""
    __tablename__ = "vip_packages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="Package name")
    level = Column(Integer, nullable=False, comment="Membership level")
    duration = Column(Integer, nullable=False, comment="Package duration (days)")
    price = Column(Numeric(10, 2), nullable=False, comment="Package price")
    description = Column(Text, nullable=True, comment="Package description")
    features = Column(JSON, nullable=True, comment="Package features")
    is_active = Column(Boolean, default=True, comment="Is active")
    create_time = Column(DateTime, default=datetime.utcnow, comment="Creation time")
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Update time")
    
    __table_args__ = (
        Index("idx_vip_packages_level_duration", "level", "duration"),
    )


class VipOrder(Base):
    """Membership order table"""
    __tablename__ = "vip_orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False, comment="Order number")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="User ID")
    package_id = Column(Integer, ForeignKey("vip_packages.id"), nullable=False, comment="Package ID")
    amount = Column(Numeric(10, 2), nullable=False, comment="Order amount")
    status = Column(String(20), default="pending", comment="Order status: pending, paid, cancelled, refunded")
    payment_method = Column(String(50), nullable=True, comment="Payment method")
    payment_time = Column(DateTime, nullable=True, comment="Payment time")
    create_time = Column(DateTime, default=datetime.utcnow, comment="Creation time")
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Update time")
    
    # Relationships
    user = relationship("User")
    package = relationship("VipPackage")
    
    __table_args__ = (
        Index("idx_vip_orders_user_status", "user_id", "status"),
        Index("idx_vip_orders_order_no", "order_no"),
    )


class MCPStore(Base):
    """MCP Store Model"""
    __tablename__ = "mcp_stores"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    icon = Column(String(255), comment="Store icon URL")
    description = Column(Text)
    store_type = Column(String(50), nullable=False)
    tags = Column(JSON, comment="Store tags as JSON list")
    content = Column(Text, comment="Store content")
    creator_id = Column(Integer, nullable=False)
    author = Column(String(255), comment="Author name")
    github_url = Column(String(255), comment="GitHub repository URL")
    tenant_id = Column(String(255), nullable=False)
    is_public = Column(Boolean, default=False, comment="Whether the store is public")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    agent_id = Column(String(36), ForeignKey("app.id"), nullable=True, comment="ID of the associated agent")

    # Relationships
    agent = relationship("App")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "store_type": self.store_type,
            "tags": self.tags or [],
            "content": self.content,
            "author": self.author,
            "github_url": self.github_url,
            "creator": self.creator_id,
            "tenant_id": self.tenant_id,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "agent_id": self.agent_id
        }


class AIImageTemplate(Base):
    """AI Image Template Model"""
    __tablename__ = 'ai_image_templates'

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, comment='Template name')
    preview_url = Column(String(255), nullable=False, comment='Preview image URL')
    description = Column(Text, nullable=True, comment='Template description')
    template_url = Column(String(255), nullable=True, comment='Template image URL')
    prompt = Column(Text, nullable=True, comment='Generation prompt')
    type = Column(Integer, nullable=False, default=1, comment='Template type: 1-Custom mode, 2-X Link mode')
    status = Column(Integer, nullable=False, default=0, comment='Template status: 0-draft, 1-active, 2-inactive')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='Create time')
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment='Update time')
