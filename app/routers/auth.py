from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
import uuid

from app.db.database import get_db
from app.models.users import User, Token as TokenModel
from app.schemas.users import (
    UserCreate, 
    UserResponse, 
    Token,
    RefreshTokenRequest
)
from app.core.security import (
    create_access_token, 
    create_refresh_token, 
    verify_refresh_token, 
    revoke_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.logging.context import get_logger
from app.config import settings

# Import exceptions from the new package
from app.exceptions import (
    ResourceAlreadyExistsError,
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError
)
from app.exceptions.utils import error_context

# Initialize router
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)

# Configure logger
logger = get_logger("api.auth", metadata={"router": "auth"})


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    Args:
        user_in: New user information
        db: Database session
        
    Returns:
        Created user
        
    Raises:
        ResourceAlreadyExistsError: If a user with the same email or username already exists
    """
    # Use error_context to add context to any exceptions
    with error_context(email=user_in.email, username=user_in.username, operation="register_user"):
        # Check if user with same email exists
        if db.query(User).filter(User.email == user_in.email).first():
            raise ResourceAlreadyExistsError(
                resource_type="User",
                message="Email already registered",
                details=[{"loc": ["body", "email"], "msg": "Email already registered"}]
            )
        
        # Check if user with same username exists
        if db.query(User).filter(User.username == user_in.username).first():
            raise ResourceAlreadyExistsError(
                resource_type="User",
                message="Username already taken",
                details=[{"loc": ["body", "username"], "msg": "Username already taken"}]
            )
        
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            email=user_in.email,
            username=user_in.username,
            hashed_password=User.get_password_hash(user_in.password),
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            organization_id=str(user_in.organization_id) if user_in.organization_id else None,
            is_active=user_in.is_active,
            is_superuser=False,  # Default to non-superuser for security reasons
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"User registered: {user.username}")
        
        return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate a user and return access and refresh tokens.
    
    Args:
        form_data: OAuth2 form with username and password
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        AuthenticationError: If authentication fails
    """
    # Use error_context to add context to any exceptions
    with error_context(username=form_data.username, operation="login"):
        # Find user by username
        user = db.query(User).filter(User.username == form_data.username).first()
        
        # Check if user exists and password is correct
        if not user or not user.verify_password(form_data.password):
            raise AuthenticationError(
                message="Incorrect username or password",
                auth_type="password",
                reason="invalid_credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationError(
                message="User account is disabled",
                auth_type="password",
                reason="account_disabled"
            )
        
        # Create token data
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "is_superuser": user.is_superuser,
        }
        
        if user.organization_id:
            token_data["organization_id"] = user.organization_id
        
        # Generate tokens
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(user.id, db)
        
        # Update last login timestamp
        user.last_login = datetime.utcnow()
        db.commit()
        
        logger.info(f"User logged in: {user.username}")
        
        # Return tokens
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        }


@router.post("/refresh", response_model=Token)
async def refresh(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh an access token using a refresh token.
    
    Args:
        refresh_data: Refresh token request
        db: Database session
        
    Returns:
        New access and refresh tokens
        
    Raises:
        TokenInvalidError: If refresh token is invalid
        TokenExpiredError: If refresh token has expired
    """
    # Use error_context to add context to any exceptions
    with error_context(operation="refresh_token"):
        try:
            # Verify refresh token
            db_token = verify_refresh_token(refresh_data.refresh_token, db)
            
            # Get user associated with token
            user = db.query(User).filter(User.id == db_token.user_id).first()
            if not user or not user.is_active:
                raise TokenInvalidError(
                    message="Invalid token or inactive user",
                    token_type="refresh",
                    reason="invalid_user"
                )
            
            # Create token data
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "is_superuser": user.is_superuser,
            }
            
            if user.organization_id:
                token_data["organization_id"] = user.organization_id
            
            # Generate new tokens
            access_token = create_access_token(token_data)
            
            # Revoke old refresh token for security
            revoke_token(refresh_data.refresh_token, db)
            
            # Create new refresh token
            new_refresh_token = create_refresh_token(user.id, db)
            
            logger.info(f"Token refreshed for user: {user.username}")
            
            # Return new tokens
            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
            }
        except Exception as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError(
                    message="Refresh token has expired",
                    token_type="refresh"
                )
            else:
                raise TokenInvalidError(
                    message="Invalid refresh token",
                    token_type="refresh",
                    reason="validation_failed"
                )


@router.post("/logout")
async def logout(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Log out a user by revoking their refresh token.
    
    Args:
        refresh_data: Refresh token request
        db: Database session
        
    Returns:
        Success message
    """
    # Revoke refresh token
    revoked = revoke_token(refresh_data.refresh_token, db)
    
    if revoked:
        logger.info("User logged out")
    
    # Always return success even if token wasn't found for security reasons
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    return current_user 