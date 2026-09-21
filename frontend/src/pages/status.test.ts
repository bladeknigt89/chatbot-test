import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import DocumentDropzone from "../components/DocumentDropzone";
import { documentProgress, documentStatusLabel } from "../components/DocumentStatus";
import type { DocumentItem } from "../services/api";

function doc(partial: Partial<DocumentItem>): DocumentItem {
  return {
    id: "1",
    agent_id: "a",
    original_filename: "x.pdf",
    mime_type: "application/pdf",
    file_size: 1,
    status: "PROCESSING",
    processing_stage: "embedding",
    progress_percent: 72,
    error_message: null,
    chunk_count: 0,
    created_at: "",
    updated_at: "",
    ...partial,
  };
}

describe("document status helpers", () => {
  it("maps stages and progress", () => {
    expect(documentStatusLabel(doc({ status: "READY", processing_stage: "ready" }))).toBe("kész");
    expect(documentStatusLabel(doc({ processing_stage: "parsing" }))).toBe("szöveg kinyerése");
    expect(documentProgress(doc({ progress_percent: 72 }))).toBe(72);
    expect(documentProgress(doc({ status: "READY", progress_percent: 0 }))).toBe(100);
  });
});

describe("document dropzone", () => {
  it("renders a visible upload button", () => {
    const html = renderToStaticMarkup(createElement(DocumentDropzone, { onFiles: () => undefined }));
    expect(html).toContain("Feltöltés");
    expect(html).toContain("500 MB");
    expect(html).toContain('type="file"');
  });
});
