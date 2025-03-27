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
    Model for tracking Terraform environment provisioning
    """

    __tablename__ = "environments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    module_path = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default=EnvironmentStatus.PENDING.value)
    variables = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(100), nullable=True)
    auto_apply = Column(String(5), nullable=False, default="True")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Execution tracking
    init_execution_id = Column(String(36), nullable=True)
    plan_execution_id = Column(String(36), nullable=True)
    apply_execution_id = Column(String(36), nullable=True)

    def __repr__(self):
        return f"<Environment(id='{self.id}', name='{self.name}', status='{self.status}')>"
