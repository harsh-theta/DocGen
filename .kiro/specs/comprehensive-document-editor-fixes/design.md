# Design Document

## Overview

This design addresses comprehensive fixes for the DocGen application's document editing and export functionality. The solution involves frontend layout improvements, enhanced HTML parsing, consistent export formatting, AI content generation improvements, and migration from Playwright to WeasyPrint for PDF generation.

## Architecture

The fixes span across multiple layers of the application:

1. **Frontend Layer**: Tiptap editor layout and table parsing improvements
2. **Backend Processing Layer**: Enhanced HTML parsing and section management
3. **AI Generation Layer**: Context-aware content generation with project-specific data
4. **Export Layer**: Unified PDF/DOCX generation with consistent formatting
5. **PDF Generation Layer**: Migration to WeasyPrint with Inter font support

## Components and Interfaces

### 1. Frontend Editor Enhancements

#### Tiptap Editor Layout Component
- **Location**: `frontend/src/pages/Preview.tsx`
- **Changes**: 
  - Modify CSS grid layout to allocate more space to editor
  - Implement responsive design with minimum 80% viewport width
  - Add table extension for proper table rendering
  - Include custom CSS for table styling

#### Table Extension Integration
- **New Component**: `frontend/src/components/TiptapTableExtension.tsx`
- **Purpose**: Enhanced table parsing and editing capabilities
- **Features**:
  - Table creation, editing, and deletion
  - Cell merging and splitting
  - Proper border and spacing rendering
  - Responsive table layout

### 2. Backend HTML Parser Improvements

#### Enhanced HTMLSectionParser
- **Location**: `backend/ai/html_parser.py`
- **Modifications**:
  - Reduce excessive section fragmentation
  - Implement intelligent content grouping
  - Maintain semantic relationships between elements
  - Improve table detection and preservation

#### Section Grouping Algorithm
```python
class IntelligentSectionGrouper:
    def group_related_content(self, sections: List[DocumentSection]) -> List[DocumentSection]:
        # Group adjacent paragraphs under same heading
        # Preserve table integrity
        # Maintain list coherence
        # Reduce micro-sections
```

### 3. AI Content Generation Enhancements

#### Context-Aware Content Generator
- **Location**: `backend/ai/content_generator.py`
- **Enhancements**:
  - Project-specific timeline calculation
  - Dynamic hour estimation based on task complexity
  - Template structure preservation with custom values
  - Reference data abstraction

#### Project Context Analyzer
```python
class ProjectContextAnalyzer:
    def analyze_project_scope(self, context: ProjectContext) -> ProjectMetrics:
        # Analyze project complexity
        # Estimate realistic timelines
        # Calculate resource requirements
        # Generate custom values instead of copying reference data
```

### 4. Unified Export System

#### Export Format Manager
- **New Component**: `backend/services/export_manager.py`
- **Purpose**: Ensure consistent formatting across PDF and DOCX exports
- **Features**:
  - Unified styling system
  - Consistent table rendering
  - Identical heading hierarchy
  - Synchronized layout parameters

#### WeasyPrint PDF Generator
- **Location**: `backend/services/weasyprint_generator.py` (new)
- **Replaces**: Current Playwright-based PDF generation
- **Features**:
  - Inter font integration
  - High-quality rendering
  - Better HTML/CSS support
  - Improved table handling

### 5. Document Formatting System

#### Clean Document Formatter
- **New Component**: `backend/services/document_formatter.py`
- **Purpose**: Handle title placement and cover page generation
- **Options**:
  - Full cover page mode
  - Clean content start mode
  - Title deduplication logic

## Data Models

### Enhanced Document Model
```python
class Document:
    # Existing fields...
    export_preferences: Optional[Dict] = None  # User export preferences
    formatting_options: Optional[Dict] = None  # Document formatting settings
    generation_metadata: Optional[Dict] = None  # Enhanced AI generation tracking
```

### Export Configuration Model
```python
class ExportConfig:
    format: str  # 'pdf' or 'docx'
    font_family: str = 'Inter'
    font_size: int = 12
    margin_settings: Dict
    header_footer_enabled: bool
    cover_page_mode: str  # 'full', 'none', 'minimal'
    table_styling: Dict
```

### Project Analysis Model
```python
class ProjectAnalysis:
    complexity_score: float
    estimated_hours: Dict[str, int]
    timeline_breakdown: Dict[str, str]
    resource_requirements: List[str]
    custom_values: Dict[str, Any]
```

## Error Handling

### Export Error Management
- Implement retry mechanisms for failed exports
- Provide specific error messages for different failure types
- Graceful degradation when advanced features fail
- User-friendly error reporting with actionable suggestions

### AI Generation Error Handling
- Fallback to template structure when AI generation fails
- Validation of generated content before saving
- Error recovery for partial generation failures
- User notification of generation issues with retry options

## Testing Strategy

### Frontend Testing
1. **Layout Testing**:
   - Viewport responsiveness across different screen sizes
   - Editor space allocation verification
   - Table rendering and editing functionality

2. **Integration Testing**:
   - Tiptap editor with enhanced table support
   - Export button functionality
   - Real-time content saving

### Backend Testing
1. **HTML Parser Testing**:
   - Section grouping algorithm validation
   - Complex document structure handling
   - Table preservation testing

2. **Export System Testing**:
   - PDF/DOCX format consistency verification
   - WeasyPrint integration testing
   - Font rendering validation

3. **AI Generation Testing**:
   - Project-specific content generation
   - Timeline calculation accuracy
   - Reference data abstraction verification

### End-to-End Testing
1. **Complete Workflow Testing**:
   - Document upload → AI generation → editing → export
   - Multiple export format consistency
   - Large document handling

2. **Performance Testing**:
   - Export speed with WeasyPrint
   - Memory usage optimization
   - Concurrent user handling

## Implementation Phases

### Phase 1: Frontend Editor Improvements
- Tiptap editor layout fixes
- Table extension integration
- Responsive design implementation

### Phase 2: Backend Processing Enhancements
- HTML parser improvements
- Section grouping algorithm
- AI content generation enhancements

### Phase 3: Export System Overhaul
- WeasyPrint integration
- Unified export formatting
- DOCX table parsing fixes

### Phase 4: Document Formatting & Polish
- Title placement fixes
- Cover page options
- Final UI/UX improvements

## Migration Strategy

### WeasyPrint Migration
1. **Parallel Implementation**: Run both Playwright and WeasyPrint systems
2. **Gradual Rollout**: A/B test with subset of users
3. **Performance Monitoring**: Compare generation times and quality
4. **Full Migration**: Switch to WeasyPrint after validation

### Data Migration
- No database schema changes required
- Export preferences stored in existing JSON fields
- Backward compatibility maintained

## Performance Considerations

### Frontend Optimizations
- Lazy loading of table extension
- Debounced content saving
- Optimized editor rendering

### Backend Optimizations
- Caching of parsed HTML structures
- Async processing for large documents
- Memory management for PDF generation

### Export Optimizations
- Streaming for large documents
- Parallel processing where possible
- Resource cleanup after generation