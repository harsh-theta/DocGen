# DocGen Project Progress

## Objective & Goal

DocGen is an AI-powered document generation system. The goal is to allow users to securely upload reference documents, edit and manage them, and generate new documents using advanced AI models. The system is designed for modularity, security, and extensibility, with a clear separation between core product features and AI orchestration.

## Completed Tasks

### Project Structure & Stack
- **Backend:** FastAPI, async SQLAlchemy, PostgreSQL, Supabase Storage.
- **Frontend:** Initially Next.js + Chakra UI, **migrated to Vite + React + shadcn/ui + Tailwind + React Router DOM** for a modern, flexible UI.
- **Directories:** Separated `backend`, `frontend`, `migrations`, `docs`, and `tests` for clear organization.

### Authentication & User Management
- Full JWT authentication flow (register, login, protected routes).
- Password hashing with passlib, JWT with python-jose.
- User model and per-user document security.

### Document Upload & Storage
- File upload endpoint with Supabase Storage integration.
- Unique, sanitized filenames; public URL returned.
- Only `.pdf`, `.docx`, and `.doc` files allowed (frontend and backend validation).
- Supabase Storage RLS policies configured for secure uploads.

### Document Metadata & Database Integration
- SQLAlchemy `Document` model and migrations.
- Metadata (user_id, filenames, URLs, etc.) saved to DB on upload.
- All document endpoints are user-specific and secure.

### Document Editing & Preview
- **Tiptap** integrated as the rich text editor in the Preview page.
- Edits are saved to the backend (`/save-edits` endpoint) and stored in the database.
- Preview page fetches document by ID and displays all metadata and content.
- Robust error handling for missing/invalid document IDs and backend errors.

### Export & Download
- Export endpoints for PDF, DOCX, and Markdown implemented in backend.
- Exported files are saved to Supabase Storage and linked to the user/document in the DB.
- Frontend export buttons trigger backend export and allow download.
- Supabase bucket creation and configuration instructions provided.
- Added direct PDF download endpoint (`/download/pdf/{id}`) to serve PDFs with proper headers.

### General Improvements
- All navigation to Preview uses the document ID from the URL.
- Defensive coding for all API calls and error states.
- Branding updated to "DocGen" everywhere.
- File type restrictions enforced in upload form.

## Pending Tasks

### Critical Issues
- **PDF Export Functionality:**
  - PDF generation works but viewing/downloading has issues.
  - When clicking the PDF export button, the download starts but Google Drive viewer fails to load the PDF.
  - PDFs are not consistently visible in Supabase cloud storage.
  - Attempted fixes include:
    - Adding proper content-type headers
    - Implementing direct download endpoint
    - Using blob approach in frontend
    - Adding download attributes to links
  - Further investigation needed to resolve this issue.

### Feature Implementation
- **AI Integration:**
  - All AI code is pending and will be implemented at the end.
  - The AI code must be completely modular and separate from the main app logic.
  - The only connection point will be the API function for document generation. Inside that endpoint, a single master function from the AI module will be called to orchestrate the AI flow.

### Polish & Testing
- **Error Handling & Edge Cases:**
  - Finalize all error handling and edge cases.
  - Add more frontend and backend tests.
  - Ensure all export formats work perfectly (PDF, DOCX, MD).
  - Final user experience polish and accessibility review.

### Deployment
- **Production Readiness:**
  - Dockerization, environment configs, and production readiness.
  - CI/CD setup if needed.

### Documentation
- **User & Developer Guides:**
  - Finalize user and developer documentation.
  - Add troubleshooting section for common issues.

## AI Integration Plan

- **Modularity:**
  - All AI logic will reside in a separate module/package.
  - The backend generation endpoint will only call a single master function from the AI code.
  - The AI module will handle all orchestration, prompt engineering, and LLM API calls (e.g., Gemini API, Langgraph, etc.).
- **Integration Point:**
  - The only connection between the main app and AI code is the API function for document generation.
  - This ensures maintainability, testability, and easy upgrades to the AI logic.
- **Timing:**
  - AI integration will be done **after** all core product features are stable and working perfectly.

## Next Steps (Prioritized)

1. **Fix PDF Export Issue:**
   - Investigate why PDFs aren't properly viewable after export
   - Test alternative approaches for serving PDFs
   - Consider implementing server-side streaming for PDF delivery

2. **Complete Export Functionality:**
   - Ensure DOCX and Markdown exports work consistently
   - Add progress indicators for large exports
   - Implement retry mechanisms for failed exports

3. **Polish User Experience:**
   - Improve error messages and feedback
   - Add loading states and transitions
   - Enhance mobile responsiveness

4. **Begin AI Integration:**
   - Only after core functionality is stable and working

## Summary

- The project is well-structured, secure, and modular.
- All core backend and frontend features (auth, upload, edit, export) are implemented.
- **PDF export functionality needs further investigation and fixes.**
- **AI integration is pending and will be modular, with a single connection point via the backend API.**
- The next step is to resolve the PDF export issue before moving to other pending tasks.