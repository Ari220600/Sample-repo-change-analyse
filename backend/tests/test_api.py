class TestAuthAPI:
    def test_register_and_login(self, client):
        r = client.post("/api/v1/auth/register", json={"email": "a@b.com", "username": "abc", "password": "pass12"})
        assert r.status_code == 201
        r = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "pass12"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_duplicate_register(self, client, user_creds):
        client.post("/api/v1/auth/register", json=user_creds)
        assert client.post("/api/v1/auth/register", json=user_creds).status_code == 409

    def test_bad_login(self, client, user_creds):
        client.post("/api/v1/auth/register", json=user_creds)
        assert client.post("/api/v1/auth/login", json={"email": user_creds["email"], "password": "x"}).status_code == 401


class TestTaskAPI:
    def test_crud_flow(self, client, auth):
        r = client.post("/api/v1/tasks", json={"title": "T1", "priority": "high"}, headers=auth)
        assert r.status_code == 201
        tid = r.json()["id"]
        assert client.get("/api/v1/tasks", headers=auth).json()[0]["title"] == "T1"
        r = client.put(f"/api/v1/tasks/{tid}", json={"status": "completed"}, headers=auth)
        assert r.json()["status"] == "completed"
        assert client.delete(f"/api/v1/tasks/{tid}", headers=auth).status_code == 204
        assert client.get(f"/api/v1/tasks/{tid}", headers=auth).status_code == 404

    def test_stats_and_profile(self, client, auth, user_creds):
        client.post("/api/v1/tasks", json={"title": "S"}, headers=auth)
        assert client.get("/api/v1/tasks/stats", headers=auth).json()["total"] == 1
        me = client.get("/api/v1/users/me", headers=auth).json()
        assert me["email"] == user_creds["email"]

    def test_unauthorized(self, client):
        assert client.get("/api/v1/tasks").status_code == 403


class TestHealth:
    def test_health(self, client):
        assert client.get("/health").json()["version"] == "1.0.0"
