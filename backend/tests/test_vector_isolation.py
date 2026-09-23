from app.vectorstore.store import SqliteVectorStore


def test_vector_store_agent_filter(tmp_path):
    store = SqliteVectorStore(tmp_path / "v.db")
    store.add_chunks(
        agent_id="a",
        document_id="d1",
        document_name="a.pdf",
        chunks=[{"id": "c1", "chunk_index": 0, "page_number": 1, "sheet_name": None, "text": "secret 12345"}],
        embeddings=[[1.0, 0.0, 0.0]],
    )
    store.add_chunks(
        agent_id="b",
        document_id="d2",
        document_name="b.pdf",
        chunks=[{"id": "c2", "chunk_index": 0, "page_number": 1, "sheet_name": None, "text": "secret 67890"}],
        embeddings=[[1.0, 0.0, 0.0]],
    )
    matches_a = store.search([1.0, 0.0, 0.0], agent_id="a", top_k=5)
    matches_b = store.search([1.0, 0.0, 0.0], agent_id="b", top_k=5)
    assert len(matches_a) == 1
    assert matches_a[0].text.endswith("12345")
    assert "67890" not in matches_a[0].text
    assert matches_b[0].text.endswith("67890")


def test_vector_store_document_filter_and_text_search(tmp_path):
    store = SqliteVectorStore(tmp_path / "v2.db")
    store.add_chunks(
        agent_id="a",
        document_id="fo",
        document_name="Fallout Core.pdf",
        chunks=[
            {"id": "c1", "chunk_index": 0, "page_number": 1, "sheet_name": None, "text": "Vault-Tec and the wasteland"},
            {"id": "c2", "chunk_index": 1, "page_number": 2, "sheet_name": None, "text": "Nuka-Cola is popular"},
        ],
        embeddings=[[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]],
    )
    store.add_chunks(
        agent_id="a",
        document_id="l5r",
        document_name="L5R Core.pdf",
        chunks=[{"id": "c3", "chunk_index": 0, "page_number": 1, "sheet_name": None, "text": "Emerald Empire clans"}],
        embeddings=[[0.0, 1.0, 0.0]],
    )
    docs = store.list_documents("a")
    assert {d[0] for d in docs} == {"fo", "l5r"}
    scoped = store.search([1.0, 0.0, 0.0], agent_id="a", top_k=5, document_ids=["fo"])
    assert all(m.document_id == "fo" for m in scoped)
    assert len(scoped) == 2
    hits = store.search_text(agent_id="a", terms=["fallout", "vault"], limit=10)
    assert any(m.document_id == "fo" for m in hits)
    assert all("l5r" != m.document_id or "fallout" in m.document_name.lower() for m in hits)