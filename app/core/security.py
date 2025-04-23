from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import jwt, JWTError
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import UUID
import secrets

from app.db.database import get_db
from app.config import settings
from app.models.users import User, Token as TokenModel
from app.schemas.users import TokenData
from app.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
    PermissionDeniedError
)
from app.exceptions.utils import error_context

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT access token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: Union[UUID, str], db: Session) -> str:
    """
    Create a refresh token and store it in the database
    
    Args:
        user_id: User ID to associate with the token
        db: Database session
        
    Returns:
        Refresh token string
    """
    # Generate a secure random token
    token_value = secrets.token_urlsafe(64)
    
    # Calculate expiration date
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store in database
    db_token = TokenModel(
        user_id=str(user_id),
        refresh_token=token_value,
        expires_at=expires_at
    )
    
    db.add(db_token)
    db.commit()
    
    return token_value


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token data
        
    Raises:
        AuthenticationError: If token is invalid
        TokenInvalidError: If token data is missing required fields
    """
    try:
        with error_context(operation="verify_token", token_type="access"):
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            organization_id: Optional[str] = payload.get("organization_id")
            is_superuser: bool = payload.get("is_superuser", False)
            
            if user_id is None or username is None:
                raise TokenInvalidError(
                    message="Invalid token data: missing required fields",
                    token_type="access",
                    reason="missing_fields"
                )
                
            token_data = TokenData(
                user_id=UUID(user_id),
                username=username,
                organization_id=UUID(organization_id) if organization_id else None,
                is_superuser=is_superuser,
                exp=payload.get("exp")
            )
            return token_data
        
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError(
                message="Token has expired",
                token_type="access"
            )
        else:
            raise AuthenticationError(
                message="Invalid authentication credentials",
                auth_type="bearer",
                reason="invalid_token",
                headers={"WWW-Authenticate": "Bearer"}
            )


def verify_refresh_token(refresh_token: str, db: Session) -> TokenModel:
    """
    Verify a refresh token against the database
    
    Args:
        refresh_token: Refresh token to verify
        db: Database session
        
    Returns:
        Token model if valid
        
    Raises:
        TokenInvalidError: If token is invalid
        TokenExpiredError: If token has expired
    """
    with error_context(operation="verify_refresh_token"):
        db_token = db.query(TokenModel).filter(
            TokenModel.refresh_token == refresh_token,
            TokenModel.is_revoked == False
        ).first()
        
        if not db_token:
            raise TokenInvalidError(
                message="Invalid refresh token",
                token_type="refresh",
                reason="not_found"
            )
            
        if db_token.expires_at <= datetime.utcnow():
            raise TokenExpiredError(
                message="Refresh token has expired",
                token_type="refresh"
            )
        
        return db_token


def revoke_token(refresh_token: str, db: Session) -> bool:
    """
    Revoke a refresh token
    
    Args:
        refresh_token: Refresh token to revoke
        db: Database session
        
    Returns:
        True if token was found and revoked, False otherwise
    """
    db_token = db.query(TokenModel).filter(
        TokenModel.refresh_token == refresh_token
    ).first()
    
    if db_token:
        db_token.is_revoked = True
        db.commit()
        return True
    
    return False


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user
    
    Args:
        token: JWT token from request
        db: Database session
        
    Returns:
        Authenticated user model
        
    Raises:
        AuthenticationError: If user not found or inactive
    """
    with error_context(operation="get_current_user"):
        token_data = verify_token(token)
        
        user = db.query(User).filter(User.id == str(token_data.user_id)).first()
        if user is None:
            raise AuthenticationError(
                message="User not found",
                auth_type="bearer",
                reason="user_not_found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_active:
            raise AuthenticationError(
                message="Inactive user",
                auth_type="bearer",
                reason="inactive_user",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure the current user is a superuser
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if superuser
        
    Raises:
        PermissionDeniedError: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise PermissionDeniedError(
            message="Not enough permissions: Superuser access required",
            permission="superuser",
            resource_type="system"
        )
    
    return current_user 