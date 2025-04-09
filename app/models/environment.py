import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class EnvironmentStatus(str, Enum):
    """Status of a Terraform environment provisioning process"""

    PENDING = "pending"
    INITIALIZING = "initializing"
    PLANNING = "planning"
    APPLYING = "applying"
    PROVISIONED = "provisioned"
    FAILED = "failed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class Environment(Base):
    """
    Model for tracking high-level deployment environments (dev, staging, prod)
    """

    __tablename__ = "environments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)  # e.g., dev, staging, prod
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=EnvironmentStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(100), nullable=True)
    
    # One-to-many relationship with resources
    resources = relationship("Resource", back_populates="environment", cascade="all, delete-orphan")

    # Environment-wide variables that apply to all resources
    global_variables = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Environment(id='{self.id}', name='{self.name}', status='{self.status}')>"
