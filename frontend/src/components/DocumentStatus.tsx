import { DocumentItem } from "../services/api";

const STAGE_LABELS: Record<string, string> = {
  uploaded: "feltöltve",
  queued: "sorban",
  parsing: "szöveg kinyerése",
  chunking: "darabolás",
  embedding: "embedding",
  ready: "kész",
  error: "hiba",
};

export function isProcessingDoc(doc: DocumentItem): boolean {
  return doc.status === "UPLOADED" || doc.status === "PROCESSING" || doc.status === "DELETING";
}

export function documentStatusLabel(doc: DocumentItem): string {
  if (doc.status === "READY") return "kész";
  if (doc.status === "ERROR") return "hiba";
  if (doc.status === "DELETING") return "törlés";
  if (doc.status === "PROCESSING" || doc.status === "UPLOADED") {
    return STAGE_LABELS[doc.processing_stage] || "feldolgozás";
  }
  return "feltöltve";
}

export function documentProgress(doc: DocumentItem): number {
  if (doc.status === "READY") return 100;
  if (doc.status === "ERROR") return Math.min(100, Math.max(0, doc.progress_percent || 0));
  if (typeof doc.progress_percent === "number") {
    return Math.min(100, Math.max(0, doc.progress_percent));
  }
  return 0;
}

export function DocumentStatus({ doc }: { doc: DocumentItem }) {
  const label = documentStatusLabel(doc);
  const percent = documentProgress(doc);
  const showBar = doc.status === "PROCESSING" || doc.status === "UPLOADED" || doc.status === "DELETING";

  return (
    <div className="doc-status">
      <span className={`badge ${doc.status.toLowerCase()}`}>
        {label}
        {showBar ? ` · ${percent}%` : ""}
      </span>
      {showBar && (
        <div className="progress-track" aria-label={`Feldolgozás ${percent}%`}>
          <div className="progress-fill" style={{ width: `${percent}%` }} />
        </div>
      )}
    </div>
  );
}
