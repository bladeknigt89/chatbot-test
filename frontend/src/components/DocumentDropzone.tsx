import { forwardRef, useImperativeHandle, useRef, useState } from "react";

const ACCEPT = ".pdf,.docx,.xlsx,.xls";
const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

type Props = {
  disabled?: boolean;
  hint?: string;
  onFiles: (files: FileList) => Promise<void> | void;
};

export type DocumentDropzoneHandle = {
  open: () => void;
};

const DocumentDropzone = forwardRef<DocumentDropzoneHandle, Props>(function DocumentDropzone(
  { disabled, hint, onFiles },
  ref
) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function openPicker() {
    if (disabled || busy) return;
    inputRef.current?.click();
  }

  useImperativeHandle(ref, () => ({ open: openPicker }));

  async function handle(files: FileList | null) {
    if (!files?.length || disabled || busy) return;
    const oversized = Array.from(files).find((file) => file.size > MAX_UPLOAD_BYTES);
    if (oversized) {
      setError("A fájl mérete meghaladja a 50 MB-os limitet.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setBusy(true);
    setError("");
    try {
      await onFiles(files);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Feltöltés sikertelen.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div
      className={`dropzone ${drag ? "active" : ""} ${disabled ? "disabled" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDrag(false);
        void handle(event.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        multiple
        accept={ACCEPT}
        disabled={disabled || busy}
        onChange={(event) => void handle(event.target.files)}
      />
      <p className="dropzone-title">Húzza ide a PDF, DOCX vagy XLSX fájlt (max. 50 MB)</p>
      {hint && <p className="muted">{hint}</p>}
      <button type="button" className="btn" disabled={disabled || busy} onClick={openPicker}>
        {busy ? "Feltöltés…" : "Feltöltés"}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  );
});

export default DocumentDropzone;
