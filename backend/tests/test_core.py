import pytest
from fastapi import HTTPException

from app.main import (
    TaskPriority,
    TaskStatus,
    authenticate_user,
    create_access_token,
    db,
    decode_token,
    hash_password,
    filter_tasks,
    task_stats,
    validate_status_change,
    verify_password,
)


class TestAuth:
    def test_password_roundtrip(self):
        h = hash_password("pass123")
        assert verify_password("pass123", h)
        assert not verify_password("wrong", h)

    def test_jwt_roundtrip(self):
        token = create_access_token(1, "a@b.com")
        assert decode_token(token)["sub"] == "1"

    def test_authenticate(self):
        db.create_user("u@x.com", "u", hash_password("p"))
        assert authenticate_user("u@x.com", "p")
        assert authenticate_user("u@x.com", "bad") is None


class TestBusinessLogic:
    def test_status_validation(self):
        validate_status_change(TaskStatus.PENDING, TaskStatus.COMPLETED)
        with pytest.raises(HTTPException):
            validate_status_change(TaskStatus.COMPLETED, TaskStatus.PENDING)

    def test_filter_and_stats(self):
        user = db.create_user("s@x.com", "s", hash_password("p"))
        db.create_task(user.id, "Alpha", None, TaskPriority.HIGH)
        db.create_task(user.id, "Beta", None, TaskPriority.LOW)
        tasks = filter_tasks(db.user_tasks(user.id), TaskStatus.PENDING, "alpha")
        assert len(tasks) == 1
        assert task_stats(user.id)["total"] == 2
