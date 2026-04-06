from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import JWT_ALGORITHM, JWT_EXPIRY_HOURS, JWT_SECRET
from app.models.user import User
from app.schemas import TokenResponse, UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Handles user registration, authentication, and status management."""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, data: UserCreate) -> User:
        """Hash the password and persist the user to the database.

        UEN validation for SELLER accounts is handled by the user-orchestrator
        before this method is called.

        Steps:
            1. Check if email already exists; raise 409 if so.
            2. If role is SELLER, ensure UEN field is present.
            3. Hash the password using bcrypt.
            4. Create the User record and commit.

        Returns:
            The newly created User ORM instance.
        """
        existing = self.db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        if data.role == "SELLER" and not data.uen:
            raise HTTPException(status_code=422, detail="UEN is required for SELLER role")

        password_hash = pwd_context.hash(data.password)

        user = User(
            email=data.email,
            password_hash=password_hash,
            full_name=data.full_name,
            role=data.role,
            uen=data.uen,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> TokenResponse:
        """Verify the user's credentials and return a signed JWT.

        Steps:
            1. Look up user by email; raise 401 if not found.
            2. Verify password against stored hash; raise 401 if mismatch.
            3. Build JWT payload with sub=user.id, role, and exp.
            4. Return TokenResponse.

        Returns:
            TokenResponse containing the access_token.
        """
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not pwd_context.verify(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
        payload = {
            "sub": str(user.id),
            "role": user.role,
            "email": user.email,
            "full_name": user.full_name,
            "iss": "invoiceflow",
            "exp": expire,
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return TokenResponse(access_token=token)

    def get_user(self, user_id: int) -> User:
        """Fetch a user by primary key.

        Raises:
            HTTPException 404 if user not found.

        Returns:
            The User ORM instance.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def update_status(self, user_id: int, status: str) -> User:
        """Set a user's account_status to ACTIVE or DEFAULTED.

        Steps:
            1. Fetch user by ID; raise 404 if not found.
            2. Update account_status field.
            3. Commit and refresh.

        Returns:
            The updated User ORM instance.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.account_status = status
        self.db.commit()
        self.db.refresh(user)
        return user
