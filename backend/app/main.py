"""TaskFlow v2 — 7 breaking changes from v1 (see v2/README.md)."""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

SECRET_KEY = "dev-secret-key"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
app = FastAPI(title="TaskFlow", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CHANGE 7: status values renamed (pending→open, completed→done)
class ItemStatus(str, Enum):
    OPEN = "open"
    DONE = "done"


class ItemPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    priority: ItemPriority = ItemPriority.MEDIUM


class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ItemStatus] = None
    priority: Optional[ItemPriority] = None


class ItemResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    status: ItemStatus
    priority: ItemPriority
    created_at: datetime
    updated_at: datetime


class ItemRecord:
    def __init__(self, id: int, user_id: int, title: str, description: Optional[str], priority: ItemPriority):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.description = description
        self.status = ItemStatus.OPEN
        self.priority = priority
        self.archived = False
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class UserRecord:
    def __init__(self, id: int, email: str, username: str, hashed_password: str):
        self.id = id
        self.email = email
        self.username = username
        self.hashed_password = hashed_password
        self.created_at = datetime.utcnow()


class Database:
    def __init__(self):
        self.users: Dict[int, UserRecord] = {}
        self.items: Dict[int, ItemRecord] = {}
        self.emails: Dict[str, int] = {}
        self._uid = self._iid = 1

    def reset(self):
        self.users.clear()
        self.items.clear()
        self.emails.clear()
        self._uid = self._iid = 1

    def create_user(self, email: str, username: str, hashed: str) -> UserRecord:
        user = UserRecord(self._uid, email, username, hashed)
        self.users[self._uid] = user
        self.emails[email] = self._uid
        self._uid += 1
        return user

    def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        uid = self.emails.get(email)
        return self.users.get(uid) if uid else None

    def get_user(self, uid: int) -> Optional[UserRecord]:
        return self.users.get(uid)

    def create_item(self, user_id: int, title: str, description: Optional[str], priority: ItemPriority) -> ItemRecord:
        item = ItemRecord(self._iid, user_id, title, description, priority)
        self.items[self._iid] = item
        self._iid += 1
        return item

    def get_item(self, iid: int) -> Optional[ItemRecord]:
        return self.items.get(iid)

    def user_items(self, user_id: int) -> List[ItemRecord]:
        return [i for i in self.items.values() if i.user_id == user_id and not i.archived]

    def save_item(self, item: ItemRecord) -> ItemRecord:
        item.updated_at = datetime.utcnow()
        self.items[item.id] = item
        return item

    def archive_item(self, iid: int) -> bool:
        item = self.items.get(iid)
        if not item:
            return False
        item.archived = True
        item.updated_at = datetime.utcnow()
        return True


db = Database()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, email: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "email": email, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> UserRecord:
    payload = decode_token(creds.credentials)
    user = db.get_user(int(payload.get("sub", 0)))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def authenticate_user(email: str, password: str) -> Optional[UserRecord]:
    user = db.get_user_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def filter_items(items: List[ItemRecord], status: Optional[ItemStatus], search: Optional[str]) -> List[ItemRecord]:
    result = items
    if status:
        result = [i for i in result if i.status == status]
    if search:
        q = search.lower()
        result = [i for i in result if q in i.title.lower() or (i.description and q in i.description.lower())]
    return sorted(result, key=lambda i: i.created_at, reverse=True)


# CHANGE 4: stats keys renamed (pending→open, completed→done)
def item_stats(user_id: int) -> dict:
    items = db.user_items(user_id)
    return {
        "total": len(items),
        "open": sum(1 for i in items if i.status == ItemStatus.OPEN),
        "done": sum(1 for i in items if i.status == ItemStatus.DONE),
        "high_priority": sum(1 for i in items if i.priority == ItemPriority.HIGH),
    }


def to_item_response(item: ItemRecord) -> ItemResponse:
    return ItemResponse(
        id=item.id, user_id=item.user_id, title=item.title, description=item.description,
        status=item.status, priority=item.priority, created_at=item.created_at, updated_at=item.updated_at,
    )


@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.0.0"}


@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=201)
def register(data: UserCreate):
    if db.get_user_by_email(data.email.lower()):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = db.create_user(data.email.lower(), data.username.strip(), hash_password(data.password))
    return UserResponse(id=user.id, email=user.email, username=user.username, created_at=user.created_at)


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(data: UserLogin):
    user = authenticate_user(data.email.lower(), data.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id, user.email))


# CHANGE 3: profile moved from /users/me to /auth/me
@app.get("/api/v1/auth/me", response_model=UserResponse)
def get_profile(user: UserRecord = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, username=user.username, created_at=user.created_at)


# CHANGE 2: tasks renamed to items
@app.post("/api/v1/items", response_model=ItemResponse, status_code=201)
def create_item(data: ItemCreate, user: UserRecord = Depends(get_current_user)):
    item = db.create_item(user.id, data.title.strip(), data.description, data.priority)
    return to_item_response(item)


@app.get("/api/v1/items", response_model=List[ItemResponse])
def list_items(
    status_filter: Optional[ItemStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    user: UserRecord = Depends(get_current_user),
):
    return [to_item_response(i) for i in filter_items(db.user_items(user.id), status_filter, search)]


@app.get("/api/v1/items/stats")
def stats(user: UserRecord = Depends(get_current_user)):
    return item_stats(user.id)


@app.get("/api/v1/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, user: UserRecord = Depends(get_current_user)):
    item = db.get_item(item_id)
    if not item or item.archived:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if item.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return to_item_response(item)


# CHANGE 6: PUT replaced with PATCH
@app.patch("/api/v1/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, data: ItemUpdate, user: UserRecord = Depends(get_current_user)):
    item = db.get_item(item_id)
    if not item or item.archived:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if item.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    if data.title is not None:
        item.title = data.title.strip()
    if data.description is not None:
        item.description = data.description
    if data.priority is not None:
        item.priority = data.priority
    if data.status is not None:
        item.status = data.status
    return to_item_response(db.save_item(item))


# CHANGE 5: DELETE replaced with archive endpoint
@app.post("/api/v1/items/{item_id}/archive", status_code=204)
def archive_item(item_id: int, user: UserRecord = Depends(get_current_user)):
    item = db.get_item(item_id)
    if not item or item.archived:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    if item.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    db.archive_item(item_id)
