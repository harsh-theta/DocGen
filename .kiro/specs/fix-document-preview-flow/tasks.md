# Implementation Plan

- [x] 1. Fix frontend API utility consolidation
  - Merge fetchWithAuth functionality into api.ts file
  - Update all imports to use consolidated API utility
  - Ensure consistent base URL usage across all API calls
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 2. Fix Preview component import and error handling
  - Update Preview.tsx to import from correct API utility
  - Improve error handling for missing document IDs
  - Add better loading states and user feedback
  - _Requirements: 1.2, 1.3_

- [x] 3. Fix backend export dependencies and error handling
  - Replace pdfkit with alternative HTML to PDF conversion
  - Improve DOCX generation with proper HTML parsing
  - Add comprehensive error handling for export endpoints
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 4. Test and verify the complete upload to preview flow
  - Test document upload navigation to preview page
  - Verify document ID is properly passed and handled
  - Test error scenarios with invalid document IDs
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 5. Test and verify export functionality
  - Test PDF export with sample content
  - Test DOCX export with sample content
  - Verify error handling and user feedback
  - _Requirements: 2.1, 2.2, 2.3, 2.4_