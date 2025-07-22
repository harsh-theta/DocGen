@router.post("/export/docx/{id}")
async def export_docx(id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Export document to DOCX format with proper table handling and consistent formatting
    
    Args:
        id: Document ID to export
        request: FastAPI request object
        db: Database session
        current_user: Authenticated user
        
    Returns:
        JSON with URL to the generated DOCX and operation tracking information
    """
    # Import error handling and progress tracking utilities
    from backend.utils.error_handler import with_export_error_handling, retry_async_operation, DOCXExportError
    from backend.utils.progress_tracker import ProgressTracker
    from backend.utils.rate_limiter import RateLimiter
    
    # Apply error handling decorator
    @with_export_error_handling("docx")
    async def process_docx_export(request_id: str):
        # Start tracking the export operation
        user_id = current_user.id
        operation_id = ProgressTracker.start_operation(
            operation_type="docx_export",
            user_id=user_id,
            document_id=id,
            metadata={"request_id": request_id}
        )
        
        # Check rate limits
        allowed, limit_info = await RateLimiter.check_rate_limit(user_id, "docx_export")
        if not allowed:
            ProgressTracker.complete_operation(
                operation_id,
                success=False,
                message=f"Rate limit exceeded. Try again in {limit_info['reset_in_seconds']} seconds."
            )
            raise DOCXExportError(
                message=f"Rate limit exceeded. Maximum {limit_info['limit']} DOCX exports per hour.",
                error_code="rate_limit_exceeded",
                retry_possible=True,
                http_status=429,
                details=limit_info
            )
        
        # Update progress - Step 1: Fetching document
        ProgressTracker.update_progress(
            operation_id,
            progress=10,
            status="in_progress",
            message="Fetching document...",
            current_step="fetch_document"
        )
        
        # Get document from database
        result = await db.execute(
            Document.__table__.select().where(Document.id == id).where(Document.user_id == user_id)
        )
        row = result.fetchone()
        if not row:
            ProgressTracker.complete_operation(
                operation_id,
                success=False,
                message="Document not found"
            )
            raise DOCXExportError(
                message="Document not found",
                error_code="document_not_found",
                retry_possible=False,
                http_status=404
            )
        
        # Get document content and title
        content = row.ai_content or "<p>No content available</p>"
        document_title = getattr(row, 'title', None) or row.name or 'Document'
        
        # Complete step 1
        ProgressTracker.complete_step(
            operation_id,
            "fetch_document",
            success=True,
            message=f"Document fetched: {document_title}"
        )
        
        # Parse HTML content
        from bs4 import BeautifulSoup
        h = BeautifulSoup(content, 'html.parser')
        
        # Define document style
        docx_style = {
            'font_family': 'Calibri',
            'font_size': 11,
            'heading_font': 'Calibri',
            'line_spacing': 1.15,
            'margins': {
                'top': 1.0,
                'right': 1.0,
                'bottom': 1.0,
                'left': 1.0
            }
        }
        
        # Update progress - Step 2: Generating DOCX
        ProgressTracker.update_progress(
            operation_id,
            progress=30,
            status="in_progress",
            message="Generating DOCX document...",
            current_step="generate_docx"
        )
        
        try:
            # Create DOCX document
            docx_buffer = io.BytesIO()
            doc = DocxDocument()
            
            # Set default font
            style = doc.styles['Normal']
            font = style.font
            font.name = docx_style['font_family']
            
            # Add document title
            doc.add_heading(document_title, 0)
            
            # Process HTML elements
            elements = h.body.find_all(recursive=False) if h.body else h.find_all(recursive=False)
            
            # Track if we're inside a list to handle nested elements
            in_list = False
            current_list = None
            list_style = None
            
            for el in elements:
                # Process element based on its type
                if el.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    level = int(el.name[1])
                    doc.add_heading(el.get_text(strip=True), level=level)
                    
                elif el.name == "p":
                    # Handle paragraphs with potential formatting
                    p = doc.add_paragraph()
                    
                    # Process inline formatting
                    for child in el.children:
                        if child.name == "b" or child.name == "strong":
                            p.add_run(child.get_text(strip=True)).bold = True
                        elif child.name == "i" or child.name == "em":
                            p.add_run(child.get_text(strip=True)).italic = True
                        elif child.name == "u":
                            p.add_run(child.get_text(strip=True)).underline = True
                        elif child.name == "a":
                            p.add_run(child.get_text(strip=True)).underline = True
                        elif child.name:
                            # Other formatted elements
                            p.add_run(child.get_text(strip=True))
                        else:
                            # Plain text
                            if child.string and child.string.strip():
                                p.add_run(child.string)
                    
                    # If paragraph was empty or only had whitespace, add the full text
                    if not p.runs:
                        p.add_run(el.get_text(strip=True))
                
                elif el.name == "table":
                    # Handle tables
                    rows = el.find_all("tr")
                    if not rows:
                        continue
                    
                    # Count columns based on the first row
                    first_row = rows[0]
                    header_cells = first_row.find_all(["th", "td"])
                    col_count = len(header_cells)
                    
                    if col_count == 0:
                        continue
                    
                    # Create table with appropriate dimensions
                    table = doc.add_table(rows=0, cols=col_count)
                    table.style = 'Table Grid'
                    
                    # Process header row if it contains th elements
                    has_header = any(cell.name == "th" for cell in header_cells)
                    
                    if has_header:
                        header_row = table.add_row()
                        for i, cell in enumerate(header_cells):
                            if i < col_count:  # Ensure we don't exceed column count
                                header_cell = header_row.cells[i]
                                # Apply header formatting
                                header_text = cell.get_text(strip=True)
                                header_cell.text = header_text
                                # Make header bold
                                for paragraph in header_cell.paragraphs:
                                    for run in paragraph.runs:
                                        run.bold = True
                    
                    # Process data rows
                    start_idx = 1 if has_header else 0
                    for row_idx in range(start_idx, len(rows)):
                        tr = rows[row_idx]
                        cells = tr.find_all(["td", "th"])
                        if cells:
                            table_row = table.add_row()
                            for i, cell in enumerate(cells):
                                if i < col_count:  # Ensure we don't exceed column count
                                    table_cell = table_row.cells[i]
                                    
                                    # Handle cell content with formatting
                                    cell_content = ""
                                    
                                    # Process cell content with potential formatting
                                    for child in cell.children:
                                        if hasattr(child, 'name') and child.name in ["p", "div"]:
                                            # Handle paragraphs within cells
                                            if table_cell.paragraphs:
                                                p = table_cell.paragraphs[0]
                                            else:
                                                p = table_cell.add_paragraph()
                                                
                                            # Process inline formatting
                                            for subchild in child.children:
                                                if hasattr(subchild, 'name'):
                                                    if subchild.name in ["b", "strong"]:
                                                        p.add_run(subchild.get_text(strip=True)).bold = True
                                                    elif subchild.name in ["i", "em"]:
                                                        p.add_run(subchild.get_text(strip=True)).italic = True
                                                    elif subchild.name == "u":
                                                        p.add_run(subchild.get_text(strip=True)).underline = True
                                                    else:
                                                        p.add_run(subchild.get_text(strip=True))
                                                elif subchild.string and subchild.string.strip():
                                                    p.add_run(subchild.string)
                                        elif hasattr(child, 'name') and child.name in ["b", "strong"]:
                                            if not table_cell.paragraphs:
                                                p = table_cell.add_paragraph()
                                            else:
                                                p = table_cell.paragraphs[0]
                                            p.add_run(child.get_text(strip=True)).bold = True
                                        elif hasattr(child, 'name') and child.name in ["i", "em"]:
                                            if not table_cell.paragraphs:
                                                p = table_cell.add_paragraph()
                                            else:
                                                p = table_cell.paragraphs[0]
                                            p.add_run(child.get_text(strip=True)).italic = True
                                        elif hasattr(child, 'name') and child.name == "u":
                                            if not table_cell.paragraphs:
                                                p = table_cell.add_paragraph()
                                            else:
                                                p = table_cell.paragraphs[0]
                                            p.add_run(child.get_text(strip=True)).underline = True
                                        elif hasattr(child, 'name') and child.name:
                                            # Other formatted elements
                                            if not table_cell.paragraphs:
                                                p = table_cell.add_paragraph()
                                            else:
                                                p = table_cell.paragraphs[0]
                                            p.add_run(child.get_text(strip=True))
                                        elif child.string and child.string.strip():
                                            # Plain text
                                            if not table_cell.paragraphs:
                                                p = table_cell.add_paragraph()
                                            else:
                                                p = table_cell.paragraphs[0]
                                            p.add_run(child.string)
                                    
                                    # If cell was empty or only had whitespace, add the full text
                                    if not table_cell.paragraphs or not table_cell.paragraphs[0].runs:
                                        table_cell.text = cell.get_text(strip=True)
                    
                    # Set table width to 100% of page width
                    table.autofit = False
                    for cell in table.columns[0].cells:
                        cell.width = Inches(6.5)  # Adjust based on page margins
                
                elif el.name in ["ul", "ol"]:
                    # Handle lists
                    for li in el.find_all("li", recursive=False):
                        list_style = "List Bullet" if el.name == "ul" else "List Number"
                        p = doc.add_paragraph(style=list_style)
                        
                        # Process inline formatting in list items
                        for child in li.children:
                            if hasattr(child, 'name'):
                                if child.name in ["b", "strong"]:
                                    p.add_run(child.get_text(strip=True)).bold = True
                                elif child.name in ["i", "em"]:
                                    p.add_run(child.get_text(strip=True)).italic = True
                                elif child.name == "u":
                                    p.add_run(child.get_text(strip=True)).underline = True
                                elif child.name:
                                    # Other formatted elements
                                    p.add_run(child.get_text(strip=True))
                            elif child.string and child.string.strip():
                                # Plain text
                                p.add_run(child.string)
                        
                        # If list item was empty or only had whitespace, add the full text
                        if not p.runs:
                            p.add_run(li.get_text(strip=True))
                        
                        # Handle nested lists (simplified approach)
                        nested_lists = li.find_all(["ul", "ol"], recursive=False)
                        for nested_list in nested_lists:
                            for nested_li in nested_list.find_all("li", recursive=False):
                                nested_style = "List Bullet 2" if nested_list.name == "ul" else "List Number 2"
                                np = doc.add_paragraph(nested_li.get_text(strip=True), style=nested_style)
            
            # Save document to buffer
            doc.save(docx_buffer)
            docx_buffer.seek(0)
            
            # Upload to storage
            supabase = request.app.state.supabase
            bucket = settings.SUPABASE_BUCKET
            safe_filename = re.sub(r'[^A-Za-z0-9._-]', '_', document_title)
            filename = f"{safe_filename}_{id}_{uuid.uuid4().hex}.docx"
            
            try:
                supabase.storage.from_(bucket).upload(filename, docx_buffer.read())
                public_url = supabase.storage.from_(bucket).get_public_url(filename)
            except Exception as e:
                logger.error(f"[DOCX Export] DOCX upload failed: {e}")
                raise HTTPException(status_code=500, detail=f"DOCX upload failed: {e}")
                
            # Update document record with export URL
            await db.execute(
                Document.__table__.update().where(Document.id == id).where(Document.user_id == user_id).values(final_file_url=public_url)
            )
            await db.commit()
            
            return {"url": public_url}
        except Exception as e:
            logger.error(f"[DOCX Export] Error: {e}")
            raise HTTPException(status_code=500, detail=f"DOCX export failed: {e}")
    
    # Generate a unique request ID
    request_id = f"docx_export_{id}_{uuid.uuid4().hex[:8]}"
    
    # Execute the export process with error handling
    return await process_docx_export(request_id=request_id)