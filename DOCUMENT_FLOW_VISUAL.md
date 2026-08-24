# Document Flow Visual - Qdrant + Registry Architecture

Visual walkthrough of how documents move through the system.

---

## 📤 Upload Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  POST /rag/documents/upload                                      │
│  Headers: X-Description, X-User-ID      Body: file (PDF/TXT)    │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
                   ┌────────────────────────┐
                   │  Validate extension    │──✗──→ 400
                   │  (.pdf / .txt only)    │
                   └───────────┬────────────┘
                               ↓
                   ┌────────────────────────┐
                   │  sha256(content)       │
                   │  Duplicate in registry?│──yes──→ 409
                   └───────────┬────────────┘
                               ↓
                   ┌────────────────────────┐
                   │  Load (PyPDF/Text)     │
                   │  Split 1000/150        │
                   │  LLM-enhance desc      │
                   └───────────┬────────────┘
                               ↓
                   ┌────────────────────────────────────────┐
                   │  Tag every chunk:                      │
                   │  {doc_id, user_id, source,             │
                   │   page, description}                   │
                   └───────────┬────────────────────────────┘
                               ↓
              ┌────────────────┴────────────────┐
              ↓                                 ↓
   ┌─────────────────────┐          ┌──────────────────────┐
   │  QDRANT upsert      │  first?  │  Mongo registry row  │
   │  vectors + payload: │─────────→│  documents collection│
   │  metadata.* tags    │ ensure   │  (vectors-first      │
   │                     │ collection│ ordering; compensate │
   └─────────────────────┘  +indexes │  on failure → 503)   │
                                     └──────────────────────┘
```

---

## 🔍 Query Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  POST /rag/query  {query, session_id, user_id}                  │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
                    ┌───────────────────────┐
                    │  Load chat history    │
                    │  (MongoDB / motor)    │
                    └───────────┬───────────┘
                                ↓
              ┌─── query_analysis (classifier node) ───┐
              │  1. list_documents(user_id)            │
              │  2. Catalogue: id | file | description │
              │  3. LLM structured output:             │
              │     route + doc_ids                    │
              │  4. doc_ids validated against registry │
              └────────────────┬───────────────────────┘
                               ↓
        route == "index" ? ── no ──→ general_llm / web_search
                               ↓ yes
        ┌─────────────────────────────────────────────┐
        │  retriever_node                             │
        │  ReAct agent rebuilt per request with:      │
        │   • tool description = selected docs' descs │
        │   • Qdrant filter:                          │
        │       user_id == <uid> AND doc_id IN [...]  │
        └────────────────┬────────────────────────────┘
                         ↓
                 grade ──no──→ rewrite ──→ retriever
                  │yes
                  ↓
              generate ──→ save to history ──→ response
```

---

## 🗑️ Delete Flow

```
DELETE /rag/documents/{doc_id}   Header: X-User-ID
        │
        ├── registry lookup ── missing/wrong owner ──→ 404
        │
        ├── count_doc_vectors(doc_id)
        │
        ├── delete registry row  ← FIRST (tombstone:
        │                           new queries can't select it)
        └── delete vectors by filter (user_id + doc_id)
                └── failure? → "vectors_removed": false in response
```

---

## 🧱 Storage Layout

```
Qdrant collection (QDRANT_DOCS_COLLECTION)
├── point: {page_content, metadata:{doc_id, user_id, source, page, description}}
├── point: {...}
└── payload indexes: metadata.doc_id, metadata.user_id  (KEYWORD)

MongoDB adaptive_rag.documents           MongoDB chat_history
├── {doc_id, user_id, filename,          ├── {session_id, type,
│    description_raw/enhanced,           │    content, timestamp}
│    content_sha256, num_chunks,         └── (async motor)
│    created_at}
├── unique(doc_id)
└── unique(user_id + content_sha256)     (sync pymongo)
```

---

## ✅ Guarantees

| Property | How |
|----------|-----|
| Persistence | Vectors in Qdrant, registry in MongoDB — restart-safe |
| Accumulation | One `doc_id` per upload, never overwritten |
| User isolation | `user_id` condition on every retrieval filter |
| No phantom docs | Registry row exists ⟺ document is searchable & listed |
| Hallucination-proof routing | Classifier `doc_ids` intersected with registry |
