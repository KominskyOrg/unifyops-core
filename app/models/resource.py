import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class ResourceStatus(str, Enum):
    """Status of a Terraform resource provisioning process"""

    PENDING = "pending"
    INITIALIZING = "initializing"
    PLANNING = "planning"
    APPLYING = "applying"
    PROVISIONED = "provisioned"
    FAILED = "failed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class Resource(Base):
    """
    Model for tracking individual Terraform resources within an environment
    """

    __tablename__ = "resources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    module_path = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=False, index=True)  # e.g., 'ec2', 's3', 'rds'
    status = Column(String(50), nullable=False, default=ResourceStatus.PENDING.value)
    variables = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(100), nullable=True)
    auto_apply = Column(String(5), nullable=False, default="True")
    
    # Link to environment
    environment_id = Column(String(36), ForeignKey("environments.id"), nullable=False, index=True)
    environment = relationship("Environment", back_populates="resources")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Execution tracking
    init_execution_id = Column(String(36), nullable=True)
    plan_execution_id = Column(String(36), nullable=True)
    apply_execution_id = Column(String(36), nullable=True)

    def __repr__(self):
        return f"<Resource(id='{self.id}', name='{self.name}', type='{self.resource_type}', status='{self.status}')>" 