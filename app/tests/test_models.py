import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.terraform import (
    Organization,
    Team,
    Environment,
    Resource,
    Connection,
    Deployment,
    StateManagement,
    EnvironmentVersion,
    CloudCredential,
    ComplianceRule,
    EnvironmentStatus,
    ResourceState,
    ConnectionType,
    DeploymentStatus
)
from app.db.database import Base, engine


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a new session
    from app.db.database import SessionLocal
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after tests
        Base.metadata.drop_all(bind=engine)


def test_organization_model(db_session):
    """Test creating and querying an Organization."""
    # Create a new organization
    org = Organization(
        name="Test Organization",
        description="Test Organization Description"
    )
    
    # Add it to the session and commit
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    
    # Verify that the organization was created with an ID
    assert org.id is not None
    assert isinstance(org.id, str)
    assert len(org.id) == 36  # UUID length
    
    # Verify that the created_at and updated_at fields were set
    assert org.created_at is not None
    assert org.updated_at is not None
    
    # Query the organization
    queried_org = db_session.query(Organization).filter(Organization.id == org.id).first()
    assert queried_org is not None
    assert queried_org.name == "Test Organization"
    assert queried_org.description == "Test Organization Description"


def test_team_model(db_session):
    """Test creating and querying a Team."""
    # Create a new organization
    org = Organization(name="Test Organization")
    db_session.add(org)
    db_session.commit()
    
    # Create a new team
    team = Team(
        name="Test Team",
        description="Test Team Description",
        organization_id=org.id
    )
    
    # Add it to the session and commit
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    
    # Verify that the team was created with an ID
    assert team.id is not None
    
    # Verify the relationship with organization
    assert team.organization is not None
    assert team.organization.id == org.id
    assert team.organization.name == "Test Organization"
    
    # Verify that the organization has the team in its teams relationship
    db_session.refresh(org)
    assert org.teams is not None
    assert len(org.teams) == 1
    assert org.teams[0].id == team.id
    assert org.teams[0].name == "Test Team"


def test_environment_model(db_session):
    """Test creating and querying an Environment."""
    # Create a new organization
    org = Organization(name="Test Organization")
    db_session.add(org)
    db_session.commit()
    
    # Create a new team
    team = Team(name="Test Team", organization_id=org.id)
    db_session.add(team)
    db_session.commit()
    
    # Create a new environment
    env = Environment(
        name="Test Environment",
        description="Test Environment Description",
        status=EnvironmentStatus.DRAFT.value,
        organization_id=org.id,
        team_id=team.id,
        created_by="test-user",
        variables={"test": "value"},
        tags={"environment": "test"}
    )
    
    # Add it to the session and commit
    db_session.add(env)
    db_session.commit()
    db_session.refresh(env)
    
    # Verify that the environment was created with an ID
    assert env.id is not None
    
    # Verify the relationship with organization and team
    assert env.organization is not None
    assert env.organization.id == org.id
    assert env.team is not None
    assert env.team.id == team.id
    
    # Verify that the JSON fields were stored correctly
    assert env.variables == {"test": "value"}
    assert env.tags == {"environment": "test"}
    
    # Verify that the environment has empty resources and deployments lists
    assert env.resources == []
    assert env.deployments == []


def test_resource_model(db_session):
    """Test creating and querying a Resource."""
    # Create a new organization and environment
    org = Organization(name="Test Organization")
    db_session.add(org)
    db_session.commit()
    
    env = Environment(
        name="Test Environment",
        organization_id=org.id,
        created_by="test-user"
    )
    db_session.add(env)
    db_session.commit()
    
    # Create a new resource
    resource = Resource(
        name="Test Resource",
        module_path="aws/vpc",
        resource_type="vpc",
        provider="aws",
        state=ResourceState.PLANNED.value,
        environment_id=env.id,
        variables={"vpc_cidr": "10.0.0.0/16"},
        position_x=100,
        position_y=100
    )
    
    # Add it to the session and commit
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)
    
    # Verify that the resource was created with an ID
    assert resource.id is not None
    
    # Verify the relationship with environment
    assert resource.environment is not None
    assert resource.environment.id == env.id
    
    # Verify that the environment has the resource in its resources relationship
    db_session.refresh(env)
    assert env.resources is not None
    assert len(env.resources) == 1
    assert env.resources[0].id == resource.id
    assert env.resources[0].name == "Test Resource"
    
    # Verify that the JSON fields were stored correctly
    assert resource.variables == {"vpc_cidr": "10.0.0.0/16"}


def test_connection_model(db_session):
    """Test creating and querying a Connection."""
    # Create a new organization and environment
    org = Organization(name="Test Organization")
    db_session.add(org)
    db_session.commit()
    
    env = Environment(
        name="Test Environment",
        organization_id=org.id,
        created_by="test-user"
    )
    db_session.add(env)
    db_session.commit()
    
    # Create two resources
    resource1 = Resource(
        name="VPC",
        module_path="aws/vpc",
        resource_type="vpc",
        provider="aws",
        environment_id=env.id
    )
    
    resource2 = Resource(
        name="Subnet",
        module_path="aws/subnet",
        resource_type="subnet",
        provider="aws",
        environment_id=env.id
    )
    
    db_session.add_all([resource1, resource2])
    db_session.commit()
    
    # Create a connection between the resources
    connection = Connection(
        source_id=resource1.id,
        target_id=resource2.id,
        connection_type=ConnectionType.NETWORK.value,
        name="VPC to Subnet",
        configuration={"subnet_cidr": "10.0.1.0/24"}
    )
    
    # Add it to the session and commit
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)
    
    # Verify that the connection was created with an ID
    assert connection.id is not None
    
    # Verify the relationships with resources
    assert connection.source_resource is not None
    assert connection.source_resource.id == resource1.id
    assert connection.target_resource is not None
    assert connection.target_resource.id == resource2.id
    
    # Verify that the resources have the connection in their relationships
    db_session.refresh(resource1)
    db_session.refresh(resource2)
    
    assert resource1.source_connections is not None
    assert len(resource1.source_connections) == 1
    assert resource1.source_connections[0].id == connection.id
    
    assert resource2.target_connections is not None
    assert len(resource2.target_connections) == 1
    assert resource2.target_connections[0].id == connection.id
    
    # Verify that the JSON field was stored correctly
    assert connection.configuration == {"subnet_cidr": "10.0.1.0/24"}


def test_deployment_model(db_session):
    """Test creating and querying a Deployment."""
    # Create a new organization and environment
    org = Organization(name="Test Organization")
    db_session.add(org)
    db_session.commit()
    
    env = Environment(
        name="Test Environment",
        organization_id=org.id,
        created_by="test-user"
    )
    db_session.add(env)
    db_session.commit()
    
    # Create a deployment
    deployment = Deployment(
        environment_id=env.id,
        execution_id=str(uuid.uuid4()),
        operation="apply",
        status=DeploymentStatus.SUCCEEDED.value,
        initiated_by="test-user",
        output="Apply complete!",
        completed_at=datetime.utcnow()
    )
    
    # Add it to the session and commit
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)
    
    # Verify that the deployment was created with an ID
    assert deployment.id is not None
    
    # Verify the relationship with environment
    assert deployment.environment is not None
    assert deployment.environment.id == env.id
    
    # Verify that the environment has the deployment in its deployments relationship
    db_session.refresh(env)
    assert env.deployments is not None
    assert len(env.deployments) == 1
    assert env.deployments[0].id == deployment.id
    assert env.deployments[0].operation == "apply"
    assert env.deployments[0].status == DeploymentStatus.SUCCEEDED.value


def test_enum_values():
    """Test that enum values match what's in the database models."""
    # Verify EnvironmentStatus enum
    assert EnvironmentStatus.DRAFT.value == "draft"
    assert EnvironmentStatus.CREATING.value == "creating"
    assert EnvironmentStatus.DEPLOYED.value == "deployed"
    assert EnvironmentStatus.FAILED.value == "failed"
    assert EnvironmentStatus.DESTROYING.value == "destroying"
    assert EnvironmentStatus.DESTROYED.value == "destroyed"
    
    # Verify ResourceState enum
    assert ResourceState.PLANNED.value == "planned"
    assert ResourceState.CREATING.value == "creating"
    assert ResourceState.CREATED.value == "created"
    assert ResourceState.UPDATING.value == "updating"
    assert ResourceState.FAILED.value == "failed"
    assert ResourceState.DESTROYING.value == "destroying"
    assert ResourceState.DESTROYED.value == "destroyed"
    
    # Verify ConnectionType enum
    assert ConnectionType.NETWORK.value == "network"
    assert ConnectionType.DEPENDS_ON.value == "depends_on"
    assert ConnectionType.DATA_FLOW.value == "data_flow"
    assert ConnectionType.SECURITY_GROUP.value == "security_group"
    
    # Verify DeploymentStatus enum
    assert DeploymentStatus.PENDING.value == "pending"
    assert DeploymentStatus.RUNNING.value == "running"
    assert DeploymentStatus.SUCCEEDED.value == "succeeded"
    assert DeploymentStatus.FAILED.value == "failed"
    assert DeploymentStatus.CANCELLED.value == "cancelled"


def test_cascade_delete_environment(db_session):
    """Test that deleting an environment cascades to its resources and deployments."""
    # Create a new organization and environment
    org = Organization(name="Test Organization")
    db_session.add(org)
    db_session.commit()
    
    env = Environment(
        name="Test Environment",
        organization_id=org.id,
        created_by="test-user"
    )
    db_session.add(env)
    db_session.commit()
    
    # Create resources and deployments
    resource1 = Resource(
        name="VPC",
        module_path="aws/vpc",
        resource_type="vpc",
        provider="aws",
        environment_id=env.id
    )
    
    resource2 = Resource(
        name="Subnet",
        module_path="aws/subnet",
        resource_type="subnet",
        provider="aws",
        environment_id=env.id
    )
    
    # Add and commit resources first to ensure they have IDs
    db_session.add_all([resource1, resource2])
    db_session.commit()
    
    deployment = Deployment(
        environment_id=env.id,
        execution_id=str(uuid.uuid4()),
        operation="apply",
        status=DeploymentStatus.SUCCEEDED.value,
        initiated_by="test-user"
    )
    
    # Create a connection between the resources after resources are committed
    connection = Connection(
        source_id=resource1.id,
        target_id=resource2.id,
        connection_type=ConnectionType.NETWORK.value,
        name="VPC to Subnet"
    )
    
    db_session.add_all([deployment, connection])
    db_session.commit()
    
    # Verify that the resources and deployment were created
    assert db_session.query(Resource).count() == 2
    assert db_session.query(Deployment).count() == 1
    assert db_session.query(Connection).count() == 1
    
    # Delete the environment
    db_session.delete(env)
    db_session.commit()
    
    # Verify that the resources, deployments, and connections were also deleted
    assert db_session.query(Resource).count() == 0
    assert db_session.query(Deployment).count() == 0
    assert db_session.query(Connection).count() == 0 