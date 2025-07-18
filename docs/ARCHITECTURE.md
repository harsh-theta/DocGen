# 🧠 DocGen MVP – System Architecture

## Overview
DocGen is an AI-powered document generation system that allows users to upload sample documents (DOCX/PDF), extract their structure, generate new content using LLMs (via LangGraph), edit in a live WYSIWYG interface, and export to DOCX/PDF. The system supports user authentication and session management.

---

## Tech Stack
| Layer           | Technology                     |
|-----------------|-------------------------------|
| Frontend        | Vite + React + shadcn/ui + Tailwind CSS + React Router DOM |
| Backend         | FastAPI (Python)               |
| Orchestration   | LangGraph                      |
| Auth            | FastAPI (JWT)                  |
| DB              | PostgreSQL                     |
| File Storage    | Supabase Storage               |
| Document Parsing| python-docx, pdfplumber        |
| DOCX Export     | python-docx, docx2pdf          |
| PDF Export      | weasyprint                     |
| LLM API         | OpenAI / Claude / Gemini (via LangGraph) |

---

## High-Level Architecture

```plaintext
                User (Web UI)
                     │
         ┌──────────▼───────────┐
         │   Frontend (React)   │
         │  - Vite + shadcn/ui + Tailwind + React Router │
         └──────────┬───────────┘
                    │
    Auth + API calls to FastAPI Backend
                    │
         ┌──────────▼────────────┐
         │  Backend (FastAPI)    │
         └──────────┬────────────┘
                    │
 ┌──────────────────┴────────────────────────┐
 │                  │                        │
 │   LangGraph Agent (LLM)         Document Parser (PDF/DOCX)   │
 │                  │                        │
 └────────→ Supabase Storage (Files) ←───────┘
                    │
               PostgreSQL
          (User, Session, File URLs, Content JSON)
```

---

## Core Modules & Responsibilities

### 1. Authentication
- User registration/login (username & password)
- Passwords hashed (passlib)
- JWT tokens for session management
- Token stored in localStorage (frontend)

### 2. Document Upload
- Users upload DOCX/PDF
- Files uploaded to Supabase Storage (`docs/original`)
- File URL stored in `documents` table (Postgres)

### 3. Document Parsing
- Backend parses DOCX/PDF
- Extracts headings, section hierarchy, styles
- Normalizes to JSON (`parsed_structure` in DB)

### 4. AI Content Generation (LangGraph)
- LangGraph agent orchestrates LLM calls
- Nodes: ParseNode, PromptMapperNode, GeneratorNode, ValidatorNode, AssemblerNode
- Output stored as `ai_content` in DB

### 5. Live Document Editing
- WYSIWYG editor (frontend, shadcn/ui + custom logic)
- Section-wise editing, saves to backend

### 6. Export (DOCX/PDF)
- Backend assembles DOCX (python-docx)
- Converts to PDF (weasyprint/docx2pdf)
- Files uploaded to Supabase Storage (`docs/generated`)
- URLs stored in `generated_docs` table

---

## Database Schema (Simplified)

### users
| id | username | hashed_password | created_at |

### documents
| id | user_id | original_file_url | parsed_structure (JSONB) | created_at |

### generated_docs
| id | document_id | ai_content (JSONB) | final_file_url | updated_at |

---

## API Endpoints (FastAPI)
| Route           | Method | Description                       |
| --------------- | ------ | --------------------------------- |
| `/register`     | POST   | User registration                 |
| `/login`        | POST   | User login + session token        |
| `/upload-doc`   | POST   | Upload file → Supabase → save URL |
| `/parse-doc`    | POST   | Parse structure into JSON         |
| `/submit-input` | POST   | Accept project-specific input     |
| `/generate`     | POST   | Run LangGraph agent               |
| `/save-edits`   | POST   | Save user-edited content          |
| `/export`       | POST   | Generate + upload final DOCX/PDF  |
| `/session/:id`  | GET    | Load a saved document session     |

---

## Data Flow Summary
1. **User registers/logs in** → receives JWT
2. **User uploads document** → file stored in Supabase, URL in DB
3. **Backend parses document** → structure saved as JSON
4. **User triggers AI generation** → LangGraph agent runs, output saved
5. **User edits content in WYSIWYG editor** → changes saved to backend
6. **User exports document** → backend generates DOCX/PDF, uploads to Supabase, URL saved

---

## Notes
- Modular codebase: clear separation of routers, services, models, and frontend components
- All API endpoints are JWT-protected except `/register` and `/login`
- Frontend uses Vite + React + shadcn/ui + Tailwind + React Router DOM (pages in `src/pages/`)
- Designed for easy extension (add new LLMs, export formats, etc.)
