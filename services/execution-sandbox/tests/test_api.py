from __future__ import annotations

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_create_python(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t1", "language": "python:3.12"})
    assert r.status_code == 200
    assert r.json()["sandbox_id"].startswith("sbx-")


def test_create_node(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t2", "language": "node:22"})
    assert r.status_code == 200
    assert r.json()["language"] == "node:22"


def test_create_with_deps(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t3", "language": "python:3.12", "dependencies": ["requests==2.32.0"]})
    assert r.status_code == 200
    sid = r.json()["sandbox_id"]
    d = client.post(f"/api/v1/sandboxes/{sid}/dependencies", json={"packages": ["requests==2.32.0"]})
    assert d.status_code == 200
    assert d.json()["all_succeeded"] is True


def test_create_with_files(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t4", "language": "python:3.12", "workspace_files": {"main.py": "print('ok')"}})
    assert r.status_code == 200
    sid = r.json()["sandbox_id"]
    files = client.get(f"/api/v1/sandboxes/{sid}/files")
    assert files.status_code == 200
    assert files.json()["total_files"] >= 1


def test_create_invalid_language(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t5", "language": "fortran:77"})
    assert r.status_code == 422


def test_create_dangerous_dep(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t6", "language": "python:3.12", "dependencies": ["pkg; rm -rf /"]})
    assert r.status_code == 422


def test_create_path_traversal_files(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t7", "language": "python:3.12", "workspace_files": {"../../etc/passwd": "bad"}})
    assert r.status_code == 422


def test_execute_code_success(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t8", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "SMOKE_RUN", "code": "print('hello')"})
    assert e.status_code == 200
    assert e.json()["exit_code"] == 0
    assert "hello" in e.json()["stdout"]


def test_execute_command_success(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t9", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "echo hi"})
    assert e.status_code == 200
    assert e.json()["exit_code"] == 0
    assert "hi" in e.json()["stdout"]


def test_execute_not_found(client):
    e = client.post("/api/v1/sandboxes/sbx-missing/execute", json={"execution_type": "CUSTOM", "command": "echo hi"})
    assert e.status_code == 404


def test_execute_blocked_command(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t10", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "docker ps"})
    assert e.status_code == 422


def test_execute_no_command_or_code(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t11", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM"})
    assert e.status_code == 422


def test_write_and_list(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t12", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    w = client.post(f"/api/v1/sandboxes/{sid}/files", json={"files": {"a.txt": "1", "b.txt": "2"}})
    assert w.status_code == 200
    l = client.get(f"/api/v1/sandboxes/{sid}/files")
    assert l.status_code == 200
    assert l.json()["total_files"] >= 2


def test_write_path_traversal(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t13", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    w = client.post(f"/api/v1/sandboxes/{sid}/files", json={"files": {"../../../bad": "x"}})
    assert w.status_code == 422


def test_read_file(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t14", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    client.post(f"/api/v1/sandboxes/{sid}/files", json={"files": {"x.txt": "content"}})
    rr = client.get(f"/api/v1/sandboxes/{sid}/files/x.txt")
    assert rr.status_code == 200
    assert rr.json()["content"] == "content"


def test_install_python(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t15", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    d = client.post(f"/api/v1/sandboxes/{sid}/dependencies", json={"packages": ["requests==2.32.0"]})
    assert d.status_code == 200
    assert d.json()["results"][0]["installed"] is True


def test_install_dangerous_package(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t16", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    d = client.post(f"/api/v1/sandboxes/{sid}/dependencies", json={"packages": ["pkg && rm -rf /"]})
    assert d.status_code == 422


def test_destroy(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t17", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    d = client.delete(f"/api/v1/sandboxes/{sid}")
    assert d.status_code == 200
    assert d.json()["status"] == "destroyed"


def test_destroy_nonexistent(client):
    d = client.delete("/api/v1/sandboxes/sbx-none")
    assert d.status_code == 404


def test_list_empty_shape(client):
    l = client.get("/api/v1/sandboxes")
    assert l.status_code == 200
    assert "total" in l.json()


def test_metrics(client):
    m = client.get("/metrics")
    assert m.status_code == 200
    assert "http_requests_total" in m.text


def test_stats_endpoint(client):
    s = client.get("/api/v1/sandboxes/stats")
    assert s.status_code == 200
    assert "total_created" in s.json()


def test_executions_listing(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t18", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "echo run"})
    ex_id = e.json()["execution_id"]
    listing = client.get(f"/api/v1/sandboxes/{sid}/executions")
    assert listing.status_code == 200
    assert any(item["execution_id"] == ex_id for item in listing.json())


def test_get_execution(client):
    r = client.post("/api/v1/sandboxes", json={"task_id": "t19", "language": "python:3.12"})
    sid = r.json()["sandbox_id"]
    e = client.post(f"/api/v1/sandboxes/{sid}/execute", json={"execution_type": "CUSTOM", "command": "echo run"})
    ex_id = e.json()["execution_id"]
    g = client.get(f"/api/v1/sandboxes/{sid}/executions/{ex_id}")
    assert g.status_code == 200
    assert g.json()["execution_id"] == ex_id
