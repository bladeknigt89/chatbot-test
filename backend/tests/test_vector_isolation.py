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
