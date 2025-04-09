import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.orm import relationship

from app.db.database import Base


class EnvironmentStatus(str, Enum):
    """Status of an environment"""
    DRAFT = "draft"
    CREATING = "creating"
    DEPLOYED = "deployed"
    FAILED = "failed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class ResourceState(str, Enum):
    """State of a resource"""
    PLANNED = "planned"
    CREATING = "creating"
    CREATED = "created"
    UPDATING = "updating"
    FAILED = "failed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class ConnectionType(str, Enum):
    """Type of connection between resources"""
    NETWORK = "network"
    DEPENDS_ON = "depends_on"
    DATA_FLOW = "data_flow"
    SECURITY_GROUP = "security_group"


class DeploymentStatus(str, Enum):
    """Status of a deployment execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Organization(Base):
    """Organization model for multi-tenant support"""
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teams = relationship("Team", back_populates="organization")
    environments = relationship("Environment", back_populates="organization")
    cloud_credentials = relationship("CloudCredential", back_populates="organization")


class Team(Base):
    """Team model for grouping users"""
    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    environments = relationship("Environment", back_populates="team")


class Environment(Base):
    """Environment model representing a collection of infrastructure resources"""
    __tablename__ = "environments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default=EnvironmentStatus.DRAFT.value)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    created_by = Column(String(255), nullable=False)  # Username or user ID
    terraform_dir = Column(String(255), nullable=True)  # Path to generated Terraform files
    variables = Column(JSON, nullable=True)  # Environment-level variables
    tags = Column(JSON, nullable=True)  # Custom tags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_deployed_at = Column(DateTime, nullable=True)
    estimated_cost = Column(Float, nullable=True)  # Estimated monthly cost

    # Relationships
    organization = relationship("Organization", back_populates="environments")
    team = relationship("Team", back_populates="environments")
    resources = relationship("Resource", back_populates="environment", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="environment", cascade="all, delete-orphan")
    state_entries = relationship("StateManagement", back_populates="environment", cascade="all, delete-orphan")
    version_history = relationship("EnvironmentVersion", back_populates="environment", cascade="all, delete-orphan")


class Resource(Base):
    """Resource model representing an infrastructure component in an environment"""
    __tablename__ = "resources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    module_path = Column(String(255), nullable=False)  # Path to the Terraform module
    resource_type = Column(String(100), nullable=False)  # Type of resource (e.g., vpc, ec2, rds)
    provider = Column(String(50), nullable=False)  # Cloud provider (e.g., aws, azure, gcp)
    state = Column(String(50), default=ResourceState.PLANNED.value)
    environment_id = Column(String(36), ForeignKey("environments.id"), nullable=False)
    variables = Column(JSON, nullable=True)  # Resource-specific variables/config
    outputs = Column(JSON, nullable=True)  # Terraform outputs for this resource
    position_x = Column(Integer, nullable=True)  # UI position X coordinate
    position_y = Column(Integer, nullable=True)  # UI position Y coordinate
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    environment = relationship("Environment", back_populates="resources")
    source_connections = relationship("Connection", back_populates="source_resource", foreign_keys="Connection.source_id", cascade="all, delete-orphan")
    target_connections = relationship("Connection", back_populates="target_resource", foreign_keys="Connection.target_id", cascade="all, delete-orphan")


class Connection(Base):
    """Connection model representing relationships between resources"""
    __tablename__ = "connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("resources.id"), nullable=False)
    target_id = Column(String(36), ForeignKey("resources.id"), nullable=False)
    connection_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    configuration = Column(JSON, nullable=True)  # Connection-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source_resource = relationship("Resource", back_populates="source_connections", foreign_keys=[source_id])
    target_resource = relationship("Resource", back_populates="target_connections", foreign_keys=[target_id])


class Deployment(Base):
    """Deployment model tracking terraform executions for an environment"""
    __tablename__ = "deployments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    environment_id = Column(String(36), ForeignKey("environments.id"), nullable=False)
    execution_id = Column(String(36), nullable=False)  # Terraform execution ID
    operation = Column(String(50), nullable=False)  # init, plan, apply, destroy, etc.
    status = Column(String(50), default=DeploymentStatus.PENDING.value)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    initiated_by = Column(String(255), nullable=False)  # Username or user ID
    output = Column(Text, nullable=True)  # Command output
    error = Column(Text, nullable=True)  # Error message if failed
    
    # Relationships
    environment = relationship("Environment", back_populates="deployments")


class StateManagement(Base):
    """Terraform state management information"""
    __tablename__ = "state_management"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    environment_id = Column(String(36), ForeignKey("environments.id"), nullable=False)
    backend_type = Column(String(50), nullable=False)  # s3, gcs, azurerm, etc.
    state_location = Column(String(255), nullable=False)  # Bucket/container path, file path, etc.
    lock_id = Column(String(255), nullable=True)  # Current lock ID if locked
    is_locked = Column(Boolean, default=False)  # Whether the state is currently locked
    last_updated = Column(DateTime, nullable=True)  # When the state was last updated
    _metadata = Column(JSON, nullable=True)  # Additional backend-specific metadata
    
    # Relationships
    environment = relationship("Environment", back_populates="state_entries")


class EnvironmentVersion(Base):
    """Version history for environments"""
    __tablename__ = "environment_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    environment_id = Column(String(36), ForeignKey("environments.id"), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)  # Full JSON snapshot of environment at this version
    changes = Column(JSON, nullable=True)  # What changed from previous version
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)  # Username or user ID
    
    # Relationships
    environment = relationship("Environment", back_populates="version_history")


class CloudCredential(Base):
    """Cloud provider credentials"""
    __tablename__ = "cloud_credentials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # aws, azure, gcp, etc.
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    credentials = Column(JSON, nullable=False)  # Encrypted credentials
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="cloud_credentials")


class ComplianceRule(Base):
    """Rules for infrastructure compliance checking"""
    __tablename__ = "compliance_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(50), nullable=False)  # security, cost, performance, etc.
    provider = Column(String(50), nullable=True)  # Specific to provider, or null for all
    resource_type = Column(String(100), nullable=True)  # Specific to resource type, or null for all
    rule_definition = Column(JSON, nullable=False)  # Rule logic in structured format
    severity = Column(String(20), nullable=False)  # high, medium, low
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 