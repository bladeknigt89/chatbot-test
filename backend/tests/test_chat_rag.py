import unicodedata

from fastapi.testclient import TestClient

from tests.conftest import HR_DOC, drain_jobs, make_pdf


def test_rag_answers_and_hallucination(admin_client: TestClient):
    agent = admin_client.post("/api/agents", json={"name": "HR"}).json()
    admin_client.post(
        f"/api/agents/{agent['id']}/documents",
        files={"file": ("munkaszabalyzat.pdf", make_pdf(HR_DOC), "application/pdf")},
    )
    drain_jobs()
    for question, expected in [
        ("Mi a vállalat neve?", "Example Kft"),
        ("Mikor van a munkaidő?", "8:00"),
        ("Hány nap szabadság jár?", "25"),
    ]:
        response = admin_client.post(
            f"/api/chat/{agent['id']}",
            json={"message": question, "stream": False},
        )
        assert response.status_code == 200, response.text
        assert expected.lower() in response.json()["message"].lower()
        assert response.json()["sources"]

    missing = admin_client.post(
        f"/api/chat/{agent['id']}",
        json={"message": "Mennyi a vállalat éves árbevétele?", "stream": False},
    )
    assert "nem található megfelelő információ" in missing.json()["message"]


def test_agent_isolation(admin_client: TestClient):
    agent_a = admin_client.post("/api/agents", json={"name": "A"}).json()
    agent_b = admin_client.post("/api/agents", json={"name": "B"}).json()
    admin_client.post(
        f"/api/agents/{agent_a['id']}/documents",
        files={"file": ("a.pdf", make_pdf("A titkos érték 12345."), "application/pdf")},
    )
    admin_client.post(
        f"/api/agents/{agent_b['id']}/documents",
        files={"file": ("b.pdf", make_pdf("A titkos érték 67890."), "application/pdf")},
    )
    drain_jobs()
    answer_a = admin_client.post(
        f"/api/chat/{agent_a['id']}",
        json={"message": "Mi a titkos érték?", "stream": False},
    ).json()["message"]
    answer_b = admin_client.post(
        f"/api/chat/{agent_b['id']}",
        json={"message": "Mi a titkos érték?", "stream": False},
    ).json()["message"]
    assert "12345" in answer_a
    assert "67890" not in answer_a
    assert "67890" in answer_b
    assert "12345" not in answer_b


def test_document_inventory_lists_all_ready_docs(admin_client: TestClient):
    agent = admin_client.post("/api/agents", json={"name": "Lib"}).json()
    for name, text in [
        ("Alpha Handbook.pdf", "Alpha handbook unique phrase ALPHA_DOC_MARKER."),
        ("Beta Codex.pdf", "Beta codex unique phrase BETA_DOC_MARKER."),
        ("Gamma Rules.pdf", "Gamma rules unique phrase GAMMA_DOC_MARKER."),
    ]:
        admin_client.post(
            f"/api/agents/{agent['id']}/documents",
            files={"file": (name, make_pdf(text), "application/pdf")},
        )
    drain_jobs()
    response = admin_client.post(
        f"/api/chat/{agent['id']}",
        json={"message": "Milyen dokumentumai vannak?", "stream": False},
    )
    assert response.status_code == 200, response.text
    message = response.json()["message"]
    assert "Alpha Handbook.pdf" in message
    assert "Beta Codex.pdf" in message
    assert "Gamma Rules.pdf" in message
    assert "3" in message
    sources = response.json()["sources"]
    assert len(sources) == 3
    names = {item["document_name"] for item in sources}
    assert names == {"Alpha Handbook.pdf", "Beta Codex.pdf", "Gamma Rules.pdf"}


def test_hungarian_questions(admin_client: TestClient):
    agent = admin_client.post("/api/agents", json={"name": "HU"}).json()
    admin_client.post(
        f"/api/agents/{agent['id']}/documents",
        files={"file": ("szerzodes.pdf", make_pdf(HR_DOC), "application/pdf")},
    )
    drain_jobs()
    questions = [
        "Mi található a dokumentum 3. fejezetében?",
        "Foglald össze röviden a dokumentumot.",
        "Milyen feltételekkel lehet igénybe venni ezt a szolgáltatást?",
        "Mennyi a szerződés időtartama?",
        "Milyen kötelezettségei vannak az ügyfélnek?",
    ]
    for question in questions:
        response = admin_client.post(
            f"/api/chat/{agent['id']}",
            json={"message": question, "stream": False},
        )
        assert response.status_code == 200
        message = response.json()["message"]
        assert len(message) > 5
        folded = "".join(
            ch for ch in unicodedata.normalize("NFD", message.lower()) if unicodedata.category(ch) != "Mn"
        )
        assert any(
            token in folded
            for token in (
                "example",
                "kft",
                "szabads",
                "probaid",
                "munkarend",
                "hatarozatlan",
                "munkaviszony",
                "informacio",
                "szabalyzat",
                "szerzodes",
            )
        )
