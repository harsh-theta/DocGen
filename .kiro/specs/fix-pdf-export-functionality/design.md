# Design Document

## Overview

The PDF export functionality needs to be completely redesigned to generate actual PDF files instead of HTML files. The current implementation creates HTML content and uploads it to Supabase storage, which results in users seeing raw HTML code when they expect a PDF.

The solution will implement proper PDF generation using a Python PDF library on the backend, with appropriate HTML-to-PDF conversion that preserves formatting and styling.

## Architecture

### Current Architecture Issues
- Backend creates HTML content instead of PDF
- HTML file is uploaded to Supabase storage
- Frontend opens HTML file URL, showing raw HTML code
- No proper PDF generation pipeline

### Proposed Architecture
- Backend will use a PDF generation library (Playwright or WeasyPrint) to convert HTML to PDF
- PDF files will be generated server-side and uploaded to Supabase storage
- Frontend will receive PDF file URLs that open properly in browsers
- Error handling for PDF generation failures

## Components and Interfaces

### Backend Components

#### PDF Generation Service
- **Location**: `backend/services/pdf_generator.py`
- **Purpose**: Handle HTML-to-PDF conversion
- **Dependencies**: Playwright or WeasyPrint library
- **Methods**:
  - `generate_pdf_from_html(html_content: str, title: str) -> bytes`
  - `sanitize_filename(filename: str) -> str`

#### Updated Export Endpoint
- **Location**: `backend/routers/documents.py`
- **Endpoint**: `POST /export/pdf/{id}`
- **Changes**: Replace HTML generation with actual PDF generation
- **Response**: Return PDF file URL instead of HTML file URL

### Frontend Components

#### Updated Preview Component
- **Location**: `frontend/src/pages/Preview.tsx`
- **Changes**: Improve error handling and user feedback
- **Features**: Better loading states and error messages

## Data Models

### Document Model Updates
No changes required to the existing Document model. The `final_file_url` field will store the PDF file URL instead of HTML file URL.

### PDF Generation Request
```typescript
interface PDFExportRequest {
  documentId: string;
  title?: string;
  includeMetadata?: boolean;
}
```

### PDF Generation Response
```typescript
interface PDFExportResponse {
  url: string;
  filename: string;
  message: string;
  size?: number;
}
```

## Error Handling

### PDF Generation Errors
- **Library Installation Issues**: Clear error message about missing dependencies
- **HTML Parsing Errors**: Fallback to plain text conversion
- **File Upload Errors**: Retry mechanism with exponential backoff
- **Storage Quota Issues**: Clear error message about storage limits

### Frontend Error Handling
- **Network Errors**: Retry mechanism with user notification
- **Invalid Response**: Clear error message and fallback options
- **Browser Compatibility**: Graceful degradation for older browsers

### Error Response Format
```json
{
  "error": "pdf_generation_failed",
  "message": "Failed to generate PDF: HTML parsing error",
  "details": "Invalid HTML structure in document content",
  "retry_possible": true
}
```

## Testing Strategy

### Unit Tests
- PDF generation service with various HTML inputs
- Filename sanitization with special characters
- Error handling for malformed HTML content
- File upload and storage operations

### Integration Tests
- End-to-end PDF export workflow
- Frontend-backend communication
- File storage and retrieval
- Error propagation from backend to frontend

### Browser Testing
- PDF viewing in different browsers
- Download functionality across browsers
- Mobile browser compatibility
- PDF file integrity verification

### Performance Tests
- Large document PDF generation
- Concurrent PDF export requests
- Memory usage during PDF generation
- Storage upload performance

## Implementation Approach

### Phase 1: Backend PDF Generation
1. Install and configure PDF generation library
2. Implement PDF generation service
3. Update export endpoint to use PDF generation
4. Add comprehensive error handling

### Phase 2: Frontend Improvements
1. Improve loading states and user feedback
2. Add better error handling and retry mechanisms
3. Update success messages and notifications

### Phase 3: Testing and Optimization
1. Comprehensive testing across browsers
2. Performance optimization for large documents
3. Error handling refinement
4. User experience improvements

## Technology Choices

### PDF Generation Library Options

#### Option 1: Playwright (Recommended)
- **Pros**: Excellent HTML/CSS support, handles modern web standards, reliable
- **Cons**: Larger dependency, requires browser installation
- **Use Case**: Best for complex HTML with modern CSS

#### Option 2: WeasyPrint
- **Pros**: Lightweight, pure Python, good CSS support
- **Cons**: Limited JavaScript support, some CSS limitations
- **Use Case**: Good for simpler HTML documents

#### Option 3: ReportLab
- **Pros**: Very fast, programmatic PDF creation
- **Cons**: Requires manual layout, no HTML conversion
- **Use Case**: Not suitable for HTML-to-PDF conversion

**Recommendation**: Use Playwright for its superior HTML/CSS rendering capabilities.

### File Storage Strategy
- Continue using Supabase storage for consistency
- Implement file cleanup for temporary files
- Add file size limits and validation
- Use unique filenames to prevent conflicts

## Security Considerations

### Input Validation
- Sanitize HTML content before PDF generation
- Validate document ownership before export
- Limit PDF file sizes to prevent abuse

### File Access Control
- Ensure PDF files are only accessible to document owners
- Implement proper authentication for export endpoints
- Add rate limiting for export operations

### Content Security
- Strip potentially malicious HTML/JavaScript
- Validate file uploads and storage operations
- Implement proper error logging without exposing sensitive data