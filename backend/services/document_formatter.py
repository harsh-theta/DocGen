"""
Document Formatter for handling title placement and cover page generation.

This module provides functionality for formatting documents with proper title
placement, cover page generation, and content organization.
"""

import re
from typing import Dict, Optional, List, Any
import logging
from bs4 import BeautifulSoup

# Setup logging
logger = logging.getLogger(__name__)

class DocumentFormatter:
    """
    Handles document formatting, title placement, and cover page generation.
    
    This class ensures consistent document structure and appearance across
    different export formats.
    """
    
    COVER_PAGE_MODES = ['full', 'minimal', 'none']
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the DocumentFormatter with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.cover_page_mode = self.config.get('cover_page_mode', 'none')
        if self.cover_page_mode not in self.COVER_PAGE_MODES:
            logger.warning(f"Invalid cover page mode: {self.cover_page_mode}. Using 'none' instead.")
            self.cover_page_mode = 'none'
    
    def remove_duplicate_titles(self, html_content: str, title: str) -> str:
        """
        Removes duplicate titles from the document.
        
        Args:
            html_content: HTML content
            title: Document title
            
        Returns:
            str: HTML content with duplicate titles removed
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all h1 elements that match the title
        h1_elements = soup.find_all('h1')
        title_elements = [h for h in h1_elements if h.get_text().strip() == title.strip()]
        
        # If there are multiple title elements, keep only the first one
        if len(title_elements) > 1:
            for title_elem in title_elements[1:]:
                title_elem.decompose()
        
        return str(soup)
    
    def generate_cover_page(self, title: str, metadata: Optional[Dict] = None) -> str:
        """
        Generates a cover page based on the specified mode.
        
        Args:
            title: Document title
            metadata: Optional document metadata
            
        Returns:
            str: HTML for the cover page
        """
        if self.cover_page_mode == 'none':
            return ""
        
        metadata = metadata or {}
        author = metadata.get('author', '')
        date = metadata.get('date', '')
        organization = metadata.get('organization', '')
        
        if self.cover_page_mode == 'full':
            return f"""
            <div class="cover-page">
                <div class="cover-content">
                    <h1 class="cover-title">{title}</h1>
                    {f'<p class="cover-author">{author}</p>' if author else ''}
                    {f'<p class="cover-organization">{organization}</p>' if organization else ''}
                    {f'<p class="cover-date">{date}</p>' if date else ''}
                </div>
                <div class="page-break"></div>
            </div>
            <style>
                .cover-page {{
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                }}
                .cover-content {{
                    max-width: 80%;
                }}
                .cover-title {{
                    font-size: 28pt;
                    margin-bottom: 24pt;
                }}
                .cover-author, .cover-organization, .cover-date {{
                    font-size: 14pt;
                    margin: 8pt 0;
                }}
            </style>
            """
        else:  # minimal
            return f"""
            <div class="minimal-cover">
                <h1 class="cover-title">{title}</h1>
                <div class="cover-meta">
                    {f'<span class="cover-author">{author}</span>' if author else ''}
                    {f'<span class="cover-organization">{organization}</span>' if organization else ''}
                    {f'<span class="cover-date">{date}</span>' if date else ''}
                </div>
                <hr class="cover-divider">
            </div>
            <style>
                .minimal-cover {{
                    margin-bottom: 24pt;
                }}
                .cover-title {{
                    font-size: 24pt;
                    margin-bottom: 8pt;
                }}
                .cover-meta {{
                    font-size: 12pt;
                    color: #666;
                    margin-bottom: 12pt;
                }}
                .cover-meta span:not(:last-child)::after {{
                    content: " | ";
                    margin: 0 5pt;
                }}
                .cover-divider {{
                    margin: 16pt 0;
                    border-top: 1pt solid #ddd;
                }}
            </style>
            """
    
    def format_document(self, html_content: str, title: str, metadata: Optional[Dict] = None) -> str:
        """
        Formats the document with proper title placement and structure.
        
        Args:
            html_content: HTML content
            title: Document title
            metadata: Optional document metadata
            
        Returns:
            str: Formatted HTML content
        """
        # Remove duplicate titles
        html_content = self.remove_duplicate_titles(html_content, title)
        
        # Generate cover page if needed
        cover_page = self.generate_cover_page(title, metadata)
        
        # If using a full cover page, remove the first title from the content
        if self.cover_page_mode == 'full':
            soup = BeautifulSoup(html_content, 'html.parser')
            first_h1 = soup.find('h1')
            if first_h1 and first_h1.get_text().strip() == title.strip():
                first_h1.decompose()
            html_content = str(soup)
        
        # Combine cover page and content
        formatted_html = f"{cover_page}{html_content}"
        
        return formatted_html