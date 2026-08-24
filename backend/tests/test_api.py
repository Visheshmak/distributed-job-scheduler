import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_and_project_flow(client: AsyncClient):
    # 1. Register User
    reg_resp = await client.post("/api/v1/auth/register", json={
        "email": "engineer@scheduler.io",
        "password": "secretpassword",
        "full_name": "Senior Engineer",
        "role": "ROLE_ADMIN"
    })
    assert reg_resp.status_code == 201
    assert reg_resp.json()["data"]["email"] == "engineer@scheduler.io"

    # 2. Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "engineer@scheduler.io",
        "password": "secretpassword"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Organization
    org_resp = await client.post("/api/v1/projects/organizations", headers=headers, json={
        "name": "Acme Cloud",
        "slug": "acme-cloud"
    })
    assert org_resp.status_code == 201
    org_id = org_resp.json()["data"]["id"]

    # 4. Create Project
    proj_resp = await client.post("/api/v1/projects", headers=headers, json={
        "organization_id": org_id,
        "name": "Payments Infra",
        "slug": "payments-infra"
    })
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["data"]["id"]

    # 5. Create Queue
    queue_resp = await client.post("/api/v1/queues", headers=headers, json={
        "project_id": proj_id,
        "name": "invoicing-queue",
        "priority": 10,
        "max_concurrency": 5,
        "status": "ACTIVE"
    })
    assert queue_resp.status_code == 201
    queue_id = queue_resp.json()["data"]["id"]

    # 6. Submit Job
    job_resp = await client.post(
        "/api/v1/jobs",
        headers={**headers, "Idempotency-Key": "invoice-12345"},
        json={
            "queue_id": queue_id,
            "project_id": proj_id,
            "job_type": "EMAIL_SEND",
            "payload": {"to": "customer@example.com", "subject": "Invoice #12345"}
        }
    )
    assert job_resp.status_code == 201
    job_data = job_resp.json()["data"]
    assert job_data["status"] == "QUEUED"
    job_id = job_data["id"]

    # 7. Test Idempotency: Submit same job with same key returns the existing job
    dup_resp = await client.post(
        "/api/v1/jobs",
        headers={**headers, "Idempotency-Key": "invoice-12345"},
        json={
            "queue_id": queue_id,
            "project_id": proj_id,
            "job_type": "EMAIL_SEND",
            "payload": {"to": "customer@example.com", "subject": "Invoice #12345"}
        }
    )
    assert dup_resp.status_code == 201
    assert dup_resp.json()["data"]["id"] == job_id

    # 8. Get Job Detail & Timeline
    detail_resp = await client.get(f"/api/v1/jobs/{job_id}/detail", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert len(detail_data["timeline"]) >= 1
    assert detail_data["timeline"][0]["event"] == "JOB_CREATED"

    # 9. Cancel Job
    cancel_resp = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["data"]["status"] == "CANCELLED"

    # 10. Pause and Resume Queue
    pause_resp = await client.post(f"/api/v1/queues/{queue_id}/pause", headers=headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["data"]["status"] == "PAUSED"

    resume_resp = await client.post(f"/api/v1/queues/{queue_id}/resume", headers=headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["data"]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_batch_job_submission(client: AsyncClient, auth_headers: dict):
    # Setup Org & Project
    org_resp = await client.post("/api/v1/projects/organizations", headers=auth_headers, json={
        "name": "Batch Org",
        "slug": "batch-org"
    })
    org_id = org_resp.json()["data"]["id"]

    proj_resp = await client.post("/api/v1/projects", headers=auth_headers, json={
        "organization_id": org_id,
        "name": "Batch Project",
        "slug": "batch-proj"
    })
    proj_id = proj_resp.json()["data"]["id"]

    queue_resp = await client.post("/api/v1/queues", headers=auth_headers, json={
        "project_id": proj_id,
        "name": "batch-queue",
        "priority": 5,
        "max_concurrency": 10
    })
    queue_id = queue_resp.json()["data"]["id"]

    # Submit Batch
    batch_resp = await client.post("/api/v1/jobs/batch", headers=auth_headers, json={
        "batch_name": "nightly-reports",
        "jobs": [
            {
                "queue_id": queue_id,
                "project_id": proj_id,
                "job_type": "DATA_PROCESSING",
                "payload": {"report_id": i}
            }
            for i in range(10)
        ]
    })
    assert batch_resp.status_code == 201
    data = batch_resp.json()["data"]
    assert data["total_jobs"] == 10
    assert data["successful_submissions"] == 10
    assert len(data["job_ids"]) == 10


@pytest.mark.asyncio
async def test_metrics_overview(client: AsyncClient, auth_headers: dict):
    metrics_resp = await client.get("/api/v1/metrics/overview", headers=auth_headers)
    assert metrics_resp.status_code == 200
    data = metrics_resp.json()["data"]
    assert "total_jobs" in data
    assert "active_workers" in data
    assert "throughput_history" in data
