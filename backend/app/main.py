"""TaskFlow v1 — single-module FastAPI app."""
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
app = FastAPI(title="TaskFlow", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
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


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None


class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime


class UserRecord:
    def __init__(self, id: int, email: str, username: str, hashed_password: str):
        self.id = id
        self.email = email
        self.username = username
        self.hashed_password = hashed_password
        self.created_at = datetime.utcnow()


class TaskRecord:
    def __init__(self, id: int, user_id: int, title: str, description: Optional[str], priority: TaskPriority):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.description = description
        self.status = TaskStatus.PENDING
        self.priority = priority
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class Database:
    def __init__(self):
        self.users: Dict[int, UserRecord] = {}
        self.tasks: Dict[int, TaskRecord] = {}
        self.emails: Dict[str, int] = {}
        self._uid = self._tid = 1

    def reset(self):
        self.users.clear()
        self.tasks.clear()
        self.emails.clear()
        self._uid = self._tid = 1

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

    def create_task(self, user_id: int, title: str, description: Optional[str], priority: TaskPriority) -> TaskRecord:
        task = TaskRecord(self._tid, user_id, title, description, priority)
        self.tasks[self._tid] = task
        self._tid += 1
        return task

    def get_task(self, tid: int) -> Optional[TaskRecord]:
        return self.tasks.get(tid)

    def user_tasks(self, user_id: int) -> List[TaskRecord]:
        return [t for t in self.tasks.values() if t.user_id == user_id]

    def save_task(self, task: TaskRecord) -> TaskRecord:
        task.updated_at = datetime.utcnow()
        self.tasks[task.id] = task
        return task

    def delete_task(self, tid: int) -> bool:
        return self.tasks.pop(tid, None) is not None


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


def validate_status_change(current: TaskStatus, new: TaskStatus) -> None:
    if current == TaskStatus.COMPLETED and new != TaskStatus.COMPLETED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot reopen completed task")
    if current == TaskStatus.CANCELLED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change cancelled task")


def filter_tasks(tasks: List[TaskRecord], status: Optional[TaskStatus], search: Optional[str]) -> List[TaskRecord]:
    result = tasks
    if status:
        result = [t for t in result if t.status == status]
    if search:
        q = search.lower()
        result = [t for t in result if q in t.title.lower() or (t.description and q in t.description.lower())]
    return sorted(result, key=lambda t: t.created_at, reverse=True)


def task_stats(user_id: int) -> dict:
    tasks = db.user_tasks(user_id)
    return {
        "total": len(tasks),
        "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
        "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
        "high_priority": sum(1 for t in tasks if t.priority == TaskPriority.HIGH),
    }


def to_task_response(task: TaskRecord) -> TaskResponse:
    return TaskResponse(
        id=task.id, user_id=task.user_id, title=task.title, description=task.description,
        status=task.status, priority=task.priority, created_at=task.created_at, updated_at=task.updated_at,
    )


@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}


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


@app.get("/api/v1/users/me", response_model=UserResponse)
def get_profile(user: UserRecord = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, username=user.username, created_at=user.created_at)


@app.post("/api/v1/tasks", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, user: UserRecord = Depends(get_current_user)):
    task = db.create_task(user.id, data.title.strip(), data.description, data.priority)
    return to_task_response(task)


@app.get("/api/v1/tasks", response_model=List[TaskResponse])
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    user: UserRecord = Depends(get_current_user),
):
    return [to_task_response(t) for t in filter_tasks(db.user_tasks(user.id), status_filter, search)]


@app.get("/api/v1/tasks/stats")
def stats(user: UserRecord = Depends(get_current_user)):
    return task_stats(user.id)


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, user: UserRecord = Depends(get_current_user)):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return to_task_response(task)


@app.put("/api/v1/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdate, user: UserRecord = Depends(get_current_user)):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    if data.title is not None:
        task.title = data.title.strip()
    if data.description is not None:
        task.description = data.description
    if data.priority is not None:
        task.priority = data.priority
    if data.status is not None:
        validate_status_change(task.status, data.status)
        task.status = data.status
    return to_task_response(db.save_task(task))


@app.delete("/api/v1/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, user: UserRecord = Depends(get_current_user)):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    db.delete_task(task_id)
