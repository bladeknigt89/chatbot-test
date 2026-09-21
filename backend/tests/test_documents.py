from fastapi.testclient import TestClient

from tests.conftest import HR_DOC, drain_jobs, make_docx, make_pdf, make_xlsx


def _agent(admin_client: TestClient) -> str:
    response = admin_client.post("/api/agents", json={"name": "Docs", "description": "teszt"})
    return response.json()["id"]


def test_pdf_upload_and_process(admin_client: TestClient):
    agent_id = _agent(admin_client)
    pdf = make_pdf(HR_DOC)
    response = admin_client.post(
        f"/api/agents/{agent_id}/documents",
        files={"file": ("munkaszabalyzat.pdf", pdf, "application/pdf")},
    )
    assert response.status_code == 202
    document_id = response.json()["id"]
    drain_jobs()
    listed = admin_client.get(f"/api/agents/{agent_id}/documents")
    doc = next(item for item in listed.json() if item["id"] == document_id)
    assert doc["status"] == "READY"
    assert doc["chunk_count"] > 0
    assert doc["progress_percent"] == 100
    assert doc["processing_stage"] == "ready"


def test_docx_and_xlsx_upload(admin_client: TestClient):
    agent_id = _agent(admin_client)
    docx = make_docx(["A vállalat neve: Example Kft."], [[["Név", "Beosztás"], ["Kiss Péter", "Fejlesztő"]]])
    xlsx = make_xlsx({"Dolgozók": [["Név", "Beosztás", "Fizetés"], ["Kiss Péter", "Fejlesztő", "650000"]]})
    pdf_resp = admin_client.post(
        f"/api/agents/{agent_id}/documents",
        files={"file": ("leiras.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    xlsx_resp = admin_client.post(
        f"/api/agents/{agent_id}/documents",
        files={"file": ("dolgozok.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert pdf_resp.status_code == 202
    assert xlsx_resp.status_code == 202
    drain_jobs()
    docs = admin_client.get(f"/api/agents/{agent_id}/documents").json()
    assert {item["status"] for item in docs} == {"READY"}


def test_document_delete_and_reprocess(admin_client: TestClient):
    agent_id = _agent(admin_client)
    response = admin_client.post(
        f"/api/agents/{agent_id}/documents",
        files={"file": ("munkaszabalyzat.pdf", make_pdf(HR_DOC), "application/pdf")},
    )
    document_id = response.json()["id"]
    drain_jobs()
    again = admin_client.post(f"/api/agents/{agent_id}/documents/{document_id}/reprocess")
    assert again.status_code == 200
    drain_jobs()
    listed = admin_client.get(f"/api/agents/{agent_id}/documents").json()
    assert listed[0]["status"] == "READY"
    deleted = admin_client.delete(f"/api/agents/{agent_id}/documents/{document_id}")
    assert deleted.status_code == 202
    drain_jobs()
    remaining = admin_client.get(f"/api/agents/{agent_id}/documents").json()
    assert remaining == []


def test_embedding_connection_error_is_user_friendly():
    from app.workers.processor import USER_EMBED_ERROR, _friendly_error

    class ConnectError(Exception):
        pass

    message = _friendly_error(ConnectError("[WinError 10061] connection refused 11434"))
    assert message == USER_EMBED_ERROR
