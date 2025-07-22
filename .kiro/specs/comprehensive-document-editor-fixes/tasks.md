# Implementation Plan

- [x] 1. Fix Tiptap editor layout and responsive design
  - Modify CSS grid layout in Preview.tsx to allocate minimum 80% viewport width to editor
  - Implement responsive design breakpoints for different screen sizes
  - Add proper spacing and padding for better text readability
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Integrate enhanced table support in Tiptap editor
  - Install and configure @tiptap/extension-table package
  - Create TiptapTableExtension component with proper table rendering
  - Add table creation, editing, and styling capabilities
  - Implement proper border, spacing, and cell alignment for tables
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Improve HTML section parser to reduce fragmentation
  - Modify HTMLSectionParser.parse_template() method to group related content intelligently
  - Implement logic to avoid creating excessive micro-sections
  - Preserve semantic relationships between headings and their content
  - Add content grouping algorithm that maintains document structure
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 4. Create WeasyPrint PDF generator service
  - Create new backend/services/weasyprint_generator.py file
  - Implement WeasyPrint-based PDF generation with Inter font support
  - Add proper CSS styling for consistent PDF formatting
  - Include error handling and validation for WeasyPrint integration
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 5. Enhance AI content generator for project-specific data
  - Modify ContentGenerator.build_prompt() to include project analysis instructions
  - Implement ProjectContextAnalyzer class for calculating project-specific timelines and hours
  - Add logic to generate custom values instead of copying reference document data
  - Create validation for generated content to ensure project relevance
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 6. Create unified export formatting system
  - Implement ExportFormatManager class to ensure consistent PDF/DOCX styling
  - Create shared CSS/styling templates for both export formats
  - Add unified table rendering logic for consistent appearance across formats
  - Implement synchronized heading hierarchy and layout parameters
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 7. Fix DOCX export table parsing and rendering
  - Enhance export_docx() function in documents.py to properly handle HTML tables
  - Implement table structure preservation in DOCX format
  - Add table header formatting and cell content preservation
  - Handle complex table layouts and multi-page table spanning
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 8. Implement clean document formatting and title management
  - Create DocumentFormatter class to handle title placement options
  - Add cover page generation logic with full-page utilization
  - Implement title deduplication to remove redundant headers
  - Create configuration options for cover page vs. clean content start
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 9. Update PDF export endpoint to use WeasyPrint
  - Modify export_pdf() function in documents.py to use new WeasyPrint generator
  - Replace Playwright-based PDF generation with WeasyPrint implementation
  - Update error handling and response formatting for new PDF generator
  - Add Inter font configuration and CSS injection for consistent typography
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 10. Add comprehensive error handling and user feedback
  - Implement specific error messages for different export failure types
  - Add retry mechanisms for failed PDF/DOCX generation
  - Create user-friendly error reporting with actionable suggestions
  - Add loading states and progress indicators for export operations
  - _Requirements: 3.1, 4.1, 7.1, 8.1_

- [ ] 11. Create integration tests for export consistency
  - Write tests to verify PDF and DOCX exports produce identical formatting
  - Add tests for table rendering consistency across both formats
  - Create tests for heading hierarchy and layout synchronization
  - Implement tests for WeasyPrint integration and font rendering
  - _Requirements: 3.1, 3.2, 3.3, 4.1, 8.4_

- [ ] 12. Optimize frontend editor performance and user experience
  - Add debounced auto-save functionality for editor content
  - Implement lazy loading for table extension to improve initial load time
  - Add keyboard shortcuts for common table operations
  - Create better visual feedback for save states and export progress
  - _Requirements: 1.1, 2.1, 2.4_