# Design Document

## Overview

This design addresses the critical issues in the DocGen document upload and preview flow. The main problems are: inconsistent API utilities, broken navigation flow from upload to preview, and non-functional export endpoints. The solution involves consolidating API utilities, fixing the navigation flow, and resolving backend export dependencies.

## Architecture

The fix involves three main areas:

1. **Frontend API Consolidation**: Merge fetchWithAuth functionality into the main api.ts file
2. **Navigation Flow Fix**: Ensure proper document ID passing from upload to preview
3. **Backend Export Fix**: Resolve missing dependencies and improve error handling

## Components and Interfaces

### Frontend API Layer

**Consolidated API Utility (`frontend/src/lib/api.ts`)**
- Merge fetchWithAuth functionality into existing api.ts
- Ensure all API calls use consistent base URL
- Maintain authentication token handling

**Updated Preview Component**
- Fix import to use consolidated API utility
- Improve error handling for missing document IDs
- Better user feedback during loading states

### Backend Export Endpoints

**Export Dependencies**
- Add proper HTML to PDF conversion without pdfkit dependency
- Improve DOCX generation with better HTML parsing
- Add comprehensive error handling

**Export Response Format**
- Consistent response structure for all export formats
- Proper error messages for debugging
- File URL validation before returning

## Data Models

No changes to existing data models are required. The Document model already supports the necessary fields for export functionality.

## Error Handling

### Frontend Error Handling
- Clear error messages for missing document IDs
- Loading states during API calls
- Graceful fallbacks for failed requests

### Backend Error Handling
- Proper exception handling in export endpoints
- Detailed error messages for debugging
- Validation of document existence before processing

### Export-Specific Error Handling
- Handle missing dependencies gracefully
- Validate content before conversion
- Proper cleanup of temporary files

## Testing Strategy

### Unit Tests
- Test API utility functions with various scenarios
- Test export endpoint error conditions
- Test navigation flow with valid/invalid document IDs

### Integration Tests
- End-to-end upload to preview flow
- Complete export workflow for both formats
- Authentication flow with API calls

### Manual Testing
- Upload document and verify preview navigation
- Test both PDF and DOCX export functionality
- Verify error messages display correctly