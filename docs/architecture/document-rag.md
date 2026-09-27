# Document RAG architecture

## Flow

```text
User
 ↓
Upload PDF (Express multipart)
 ↓
Store file under data/documents/{userId}/{projectId}/
 ↓
MongoDB metadata (status=processing)
 ↓
POST FastAPI /api/v1/documents/process
 ↓
Parse (PyMuPDF) → Chunk → Embed (FastEmbed) → Chroma
 ↓
Mark document ready
 ↓
Start research with documentIds + optional web
 ↓
Retrieve document chunks + web sources
 ↓
Evidence → Claims → Fact Checker → Analyst → Report
```

## Upload

- `POST /api/v1/projects/:projectId/documents` (multipart `files`)
- Validates auth, project ownership, PDF magic bytes, size limits
- Safe internal filenames; never trusts client MIME alone
- Returns `{ documentId, status: "processing" }`

## Processing

- AI service endpoint: `POST /api/v1/documents/process`
- Constrains paths to `documents_dir`
- Uses stable `document_id` (Mongo ObjectId) for chunk IDs
- Skips re-embedding when chunks already exist for that id

## Hybrid retrieval

Research request may include:

- `enableWebSearch`
- `enableDocumentResearch` / `enablePdfRag`
- `documentIds[]`

Express resolves owned, **ready** documents to absolute paths + ids and forwards them to FastAPI.

The workflow:

1. Retrieves document sources (filtered by `document_ids`)
2. Runs web research when enabled
3. Merges sources for extraction / fact-check / analysis / writing

## Citations

Document sources carry metadata:

- `source_kind: document`
- `document_id`, `page`, `chunk_id`, `filename`
- `citation: "[Document: file.pdf, p. 42]"`

UI Sources tab separates **Web Sources** vs **Documents**; document cards open an excerpt panel (no filesystem paths exposed).

## Security

- Auth + ownership on all document routes
- Path traversal blocked in storage + AI path resolve
- PDF header check (`%PDF-`)
- Prompt content from PDFs is treated as untrusted data by existing agent prompts
- Absolute paths stripped from public API source payloads

## Limitations

- Text-extractable PDFs only (no OCR for scanned pages)
- PDF only (no DOCX)
- Local filesystem storage (S3-ready interface, not implemented)
- Global Chroma collection with metadata filters (not per-tenant collections)
