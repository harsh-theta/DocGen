"""
Export Format Manager for consistent PDF/DOCX styling.

This module provides a unified approach to document formatting across different
export formats, ensuring consistent styling, layout, and rendering.
"""

import os
from typing import Dict, Optional, List, Any
import logging
from pathlib import Path

from backend.services.document_formatter import DocumentFormatter

# Setup logging
logger = logging.getLogger(__name__)

class ExportFormatManager:
    """
    Manages consistent formatting across PDF and DOCX exports.
    
    This class ensures that documents exported in different formats maintain
    consistent styling, layout, and appearance.
    """
    
    # Default font settings
    DEFAULT_FONT_FAMILY = 'Inter'
    DEFAULT_FONT_SIZE = 12
    DEFAULT_HEADING_SIZES = {
        'h1': 24,
        'h2': 20,
        'h3': 16,
        'h4': 14,
        'h5': 13,
        'h6': 12
    }
    
    # Default margin settings (in mm for PDF, pt for DOCX)
    DEFAULT_MARGINS = {
        'top': 25,
        'right': 25,
        'bottom': 25,
        'left': 25
    }
    
    # Default table styling
    DEFAULT_TABLE_STYLE = {
        'border_color': '#dddddd',
        'border_width': '1px',
        'header_bg_color': '#f3f3f3',
        'cell_padding': '8px',
        'text_align': 'left'
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the ExportFormatManager with optional configuration.
        
        Args:
            config: Optional configuration dictionary to override defaults
        """
        self.config = config or {}
        self.font_family = self.config.get('font_family', self.DEFAULT_FONT_FAMILY)
        self.font_size = self.config.get('font_size', self.DEFAULT_FONT_SIZE)
        self.margins = self.config.get('margins', self.DEFAULT_MARGINS)
        self.table_style = self.config.get('table_style', self.DEFAULT_TABLE_STYLE)
        self.heading_sizes = self.config.get('heading_sizes', self.DEFAULT_HEADING_SIZES)
        
        # Path to static resources
        self.static_dir = Path(os.path.dirname(os.path.dirname(__file__))) / 'static'
        self.fonts_dir = self.static_dir / 'fonts'
        
    def get_css_template(self) -> str:
        """
        Returns a CSS template with consistent styling for both PDF and HTML/CSS-based exports.
        
        Returns:
            str: CSS styling template
        """
        css_path = self.static_dir / 'css' / 'export_templates.css'
        try:
            with open(css_path, 'r') as css_file:
                css_content = css_file.read()
                
            # Replace any placeholders with dynamic values if needed
            css_content = css_content.replace('font-family: \'Inter\'', f'font-family: \'{self.font_family}\'')
            css_content = css_content.replace('font-size: 12pt', f'font-size: {self.font_size}pt')
            css_content = css_content.replace('margin: 25mm 25mm 25mm 25mm', 
                                             f'margin: {self.margins["top"]}mm {self.margins["right"]}mm {self.margins["bottom"]}mm {self.margins["left"]}mm')
            
            return css_content
        except (FileNotFoundError, IOError) as e:
            logger.error(f"Failed to load CSS template: {e}")
            # Fall back to inline CSS if file can't be loaded
            return self._generate_fallback_css()
    
    def get_docx_style_dict(self) -> Dict[str, Any]:
        """
        Returns styling parameters for DOCX document generation.
        
        Returns:
            Dict: DOCX styling parameters
        """
        return {
            'font_family': self.font_family,
            'font_size': self.font_size,
            'margins': {
                # Convert mm to DOCX-compatible units (twips, 1/20th of a point)
                'top': self.margins['top'] * 2.835,  # mm to twips
                'right': self.margins['right'] * 2.835,
                'bottom': self.margins['bottom'] * 2.835,
                'left': self.margins['left'] * 2.835
            },
            'heading_sizes': self.heading_sizes,
            'table_style': {
                'border_color': self.table_style['border_color'],
                'border_width': int(self.table_style['border_width'].replace('px', '')),
                'header_bg_color': self.table_style['header_bg_color'],
                'cell_padding': int(self.table_style['cell_padding'].replace('px', '')),
                'text_align': self.table_style['text_align']
            }
        }
    
    def get_table_html_template(self) -> str:
        """
        Returns a consistent HTML table template for both export formats.
        
        Returns:
            str: HTML table template
        """
        return f"""
        <table style="width:100%; border-collapse:collapse; margin-bottom:15pt; border:{self.table_style['border_width']} solid {self.table_style['border_color']}">
            <thead>
                <tr>
                    <th style="background-color:{self.table_style['header_bg_color']}; text-align:{self.table_style['text_align']}; padding:{self.table_style['cell_padding']}; border:{self.table_style['border_width']} solid {self.table_style['border_color']}; font-weight:bold;">{{header_content}}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding:{self.table_style['cell_padding']}; border:{self.table_style['border_width']} solid {self.table_style['border_color']}; text-align:{self.table_style['text_align']};">{{cell_content}}</td>
                </tr>
            </tbody>
        </table>
        """
    
    def apply_consistent_table_styling(self, html_content: str) -> str:
        """
        Applies consistent table styling to HTML content.
        
        Args:
            html_content: HTML content with tables
            
        Returns:
            str: HTML with consistently styled tables
        """
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            # Add consistent styling to table
            table['style'] = f"width:100%; border-collapse:collapse; margin-bottom:15pt; border:{self.table_style['border_width']} solid {self.table_style['border_color']}"
            
            # Style headers
            headers = table.find_all('th')
            for th in headers:
                th['style'] = f"background-color:{self.table_style['header_bg_color']}; text-align:{self.table_style['text_align']}; padding:{self.table_style['cell_padding']}; border:{self.table_style['border_width']} solid {self.table_style['border_color']}; font-weight:bold;"
            
            # Style cells
            cells = table.find_all('td')
            for td in cells:
                td['style'] = f"padding:{self.table_style['cell_padding']}; border:{self.table_style['border_width']} solid {self.table_style['border_color']}; text-align:{self.table_style['text_align']};"
        
        return str(soup)
    
    def apply_heading_hierarchy(self, html_content: str) -> str:
        """
        Applies consistent heading hierarchy to HTML content.
        
        Args:
            html_content: HTML content with headings
            
        Returns:
            str: HTML with consistently styled headings
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for level in range(1, 7):
            tag = f'h{level}'
            headings = soup.find_all(tag)
            for heading in headings:
                heading['style'] = f"font-size:{self.heading_sizes[tag]}pt; font-family:'{self.font_family}', sans-serif; margin-top:{int(self.heading_sizes[tag])}pt; margin-bottom:{int(self.heading_sizes[tag]/2)}pt;"
        
        return str(soup)
    
    def prepare_html_for_export(self, html_content: str) -> str:
        """
        Prepares HTML content for export by applying consistent styling.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            str: HTML with consistent styling for export
        """
        # Apply table styling
        html_content = self.apply_consistent_table_styling(html_content)
        
        # Apply heading hierarchy
        html_content = self.apply_heading_hierarchy(html_content)
        
        # Wrap with full HTML structure and CSS
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
            {self.get_css_template()}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return full_html
    
    def _generate_fallback_css(self) -> str:
        """
        Generates a fallback CSS template when the external CSS file cannot be loaded.
        
        Returns:
            str: Fallback CSS styling template
        """
        return f"""
        @font-face {{
            font-family: '{self.font_family}';
            src: url('{self.fonts_dir / "Inter-Regular.ttf"}') format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        
        @font-face {{
            font-family: '{self.font_family}';
            src: url('{self.fonts_dir / "Inter-Bold.ttf"}') format('truetype');
            font-weight: bold;
            font-style: normal;
        }}
        
        @font-face {{
            font-family: '{self.font_family}';
            src: url('{self.fonts_dir / "Inter-Italic.ttf"}') format('truetype');
            font-weight: normal;
            font-style: italic;
        }}
        
        body {{
            font-family: '{self.font_family}', sans-serif;
            font-size: {self.font_size}pt;
            line-height: 1.5;
            margin: {self.margins['top']}mm {self.margins['right']}mm {self.margins['bottom']}mm {self.margins['left']}mm;
            color: #333333;
        }}
        
        h1 {{ font-size: {self.heading_sizes['h1']}pt; margin-top: 24pt; margin-bottom: 12pt; }}
        h2 {{ font-size: {self.heading_sizes['h2']}pt; margin-top: 20pt; margin-bottom: 10pt; }}
        h3 {{ font-size: {self.heading_sizes['h3']}pt; margin-top: 16pt; margin-bottom: 8pt; }}
        h4 {{ font-size: {self.heading_sizes['h4']}pt; margin-top: 14pt; margin-bottom: 7pt; }}
        h5 {{ font-size: {self.heading_sizes['h5']}pt; margin-top: 12pt; margin-bottom: 6pt; }}
        h6 {{ font-size: {self.heading_sizes['h6']}pt; margin-top: 12pt; margin-bottom: 6pt; }}
        
        p {{ margin-top: 0; margin-bottom: 10pt; }}
        
        ul, ol {{ margin-bottom: 10pt; padding-left: 20pt; }}
        li {{ margin-bottom: 5pt; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15pt;
            border: {self.table_style['border_width']} solid {self.table_style['border_color']};
        }}
        
        th {{
            background-color: {self.table_style['header_bg_color']};
            text-align: {self.table_style['text_align']};
            padding: {self.table_style['cell_padding']};
            border: {self.table_style['border_width']} solid {self.table_style['border_color']};
            font-weight: bold;
        }}
        
        td {{
            padding: {self.table_style['cell_padding']};
            border: {self.table_style['border_width']} solid {self.table_style['border_color']};
            text-align: {self.table_style['text_align']};
        }}
        
        img {{ max-width: 100%; height: auto; }}
        
        .page-break {{ page-break-after: always; }}
        
        a {{ color: #0066cc; text-decoration: underline; }}
        
        pre, code {{
            font-family: 'Courier New', monospace;
            background-color: #f5f5f5;
            padding: 2pt;
            border-radius: 3pt;
        }}
        
        pre {{
            padding: 8pt;
            overflow-x: auto;
            margin-bottom: 10pt;
        }}
        
        blockquote {{
            margin-left: 20pt;
            padding-left: 10pt;
            border-left: 3pt solid #dddddd;
            color: #666666;
        }}
        
        hr {{
            border: none;
            border-top: 1px solid #dddddd;
            margin: 15pt 0;
        }}
        """
        
    def get_export_config(self, format_type: str) -> Dict[str, Any]:
        """
        Returns export configuration for the specified format.
        
        Args:
            format_type: Export format ('pdf' or 'docx')
            
        Returns:
            Dict: Format-specific export configuration
        """
        if format_type.lower() == 'pdf':
            return {
                'css': self.get_css_template(),
                'font_paths': {
                    'regular': str(self.fonts_dir / "Inter-Regular.ttf"),
                    'bold': str(self.fonts_dir / "Inter-Bold.ttf"),
                    'italic': str(self.fonts_dir / "Inter-Italic.ttf")
                },
                'margins': self.margins,
                'font_family': self.font_family,
                'font_size': self.font_size
            }
        elif format_type.lower() == 'docx':
            return self.get_docx_style_dict()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")