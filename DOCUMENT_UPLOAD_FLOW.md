# Document Upload Flow - How New Documents Are Stored

How documents flow through the system with the persistent multi-document
Qdrant backend.

---

## 📊 Complete Document Upload & Retrieval Flow

### **Step 1: User Uploads a Document (Via Streamlit or API)**

```
POST /rag/documents/upload
Headers: X-Description: "My document description"
         X-User-ID: alice
Body: file (PDF or TXT)
```

**What happens in `document_upload.py` (`ingest_document`):**

1. **File Validation**
   Only `.pdf` and `.txt` are accepted (`UnsupportedFileTypeError` → HTTP 400).

2. **Duplicate Detection**
   The file's SHA-256 is checked against the caller's registry entries.
   Identical content already uploaded → `DuplicateDocumentError` → HTTP 409.

3. **Load Document Content**
   ```python
   loader = PyPDFLoader(tmp_path) if .pdf else TextLoader(tmp_path)
   docs = loader.load()
   ```

4. **Enhance Description with LLM**
   `enhance_description_with_llm(description)` turns the user's one-liner
   into a strict retriever-tool instruction.

5. **Split Document into Chunks**
   `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)`.

6. **Tag Every Chunk** — metadata is rebuilt explicitly:
   ```python
   chunk.metadata = {
       "doc_id": <uuid4 hex>, "user_id": "alice",
       "source": filename, "page": <page>, "description": enhanced,
   }
   ```

7. **Store Vectors in Qdrant** (`retriever_setup.upsert_chunks`)
   Chunks are embedded into one shared collection
   (`QDRANT_DOCS_COLLECTION`). The collection and payload indexes on
   `metadata.doc_id` / `metadata.user_id` are created automatically on the
   first upload. **Vectors are written before the registry row**, so a row
   always implies a searchable document.

8. **Register in MongoDB** (`db/document_registry.py`)
   One row per document: `{doc_id, user_id, filename, description_raw,
   description_enhanced, content_sha256, num_chunks, created_at}`.
   If registration fails after vectors were written, the vectors are
   deleted again (compensation).

---

### **Step 2: Query Process - Scoped Retrieval**

```
POST /rag/query
{ "query": "...", "session_id": "...", "user_id": "alice" }
```

**Flow:**

1. `query_classifier` loads the user's document registry rows and shows the
   LLM a catalogue of `id | filename | description`.
2. The classifier returns a route **plus the relevant `doc_ids`** (validated
   against the registry — hallucinated or cross-user IDs are dropped).
3. If routed to `"index"`, `retriever_node` builds a retriever whose Qdrant
   filter combines `metadata.user_id == alice` **and**
   `metadata.doc_id ∈ selected`. Users can never see each other's content.
4. Retrieved chunks pass through grade → rewrite → generate as before.

---

## 🔄 Document Lifecycle

```
Upload ──→ validate ──→ dedup check ──→ load & chunk ──→ tag metadata
                                                              │
        ┌─────────────────────────────────────────────────────┘
        ↓
  Qdrant upsert (vectors first) ──→ Mongo registry row
        │                                  │
        │  failure?                        │  failure?
        │  → HTTP 503                      │  → delete vectors, HTTP 503
        ↓
  Searchable & listed

Delete: registry row removed FIRST (tombstone) → then vectors by filter.
In-flight queries may still see just-deleted points; new ones cannot.
```

---

## 🎯 Key Points

- **Persistence**: everything lives in Qdrant + MongoDB — documents survive
  server restarts. There is no dummy/placeholder document anywhere anymore.
- **Accumulation**: uploads never overwrite each other; every document gets
  its own `doc_id` and registry entry.
- **Isolation**: all retrieval filters include `user_id`, so isolation holds
  even if someone guesses another user's `doc_id`.
- **Management**: list with `GET /rag/documents`, delete with
  `DELETE /rag/documents/{doc_id}` (owner-checked, 404 otherwise).

---

## 🔧 Technical Details

### Where Things Live

| Concern | Technology | Location |
|---------|-----------|----------|
| Vector storage | Qdrant collection (`QDRANT_DOCS_COLLECTION`) | `src/db/qdrant_client.py`, `src/rag/retriever_setup.py` |
| Document registry | MongoDB `documents` collection (sync pymongo) | `src/db/document_registry.py` |
| Chat history | MongoDB via async motor | `src/memory/chat_history_mongo.py` |

### Filter Shape

langchain-qdrant stores `Document.metadata` under the payload key
`"metadata"`, so filters use dotted keys:

```python
Filter(must=[
    FieldCondition(key="metadata.user_id", match=MatchValue(value=user_id)),
    FieldCondition(key="metadata.doc_id", match=MatchAny(any=doc_ids)),  # optional
])
```

---

## 💡 How to Test

```bash
# 1. Upload
curl -X POST http://localhost:8000/rag/documents/upload \
  -H "X-User-ID: alice" \
  -H "X-Description: Python Programming Guide" \
  -F "file=@python_guide.pdf"

# 2. List (should show the upload)
curl http://localhost:8000/rag/documents -H "X-User-ID: alice"

# 3. Query
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is Python?","session_id":"s1","user_id":"alice"}'

# 4. Verify vector count matches num_chunks
curl "$QDRANT_URL/collections/<docs-collection>/points/count" \
  -H 'Content-Type: application/json' \
  -d '{"filter":{"must":[{"key":"metadata.doc_id","match":{"value":"<doc_id>"}}]},"exact":true}'

# 5. Delete
curl -X DELETE http://localhost:8000/rag/documents/<doc_id> -H "X-User-ID: alice"
```

---

**Status**: ✅ Persistent multi-document storage active
