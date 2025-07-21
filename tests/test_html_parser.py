"""
Tests for the HTML section parser.

This module contains tests for the HTMLSectionParser class, which is responsible
for parsing HTML documents into semantic sections.
"""

import pytest
from bs4 import BeautifulSoup
from backend.ai.html_parser import HTMLSectionParser, SectionBoundary
from backend.ai.models import DocumentSection, SectionType, SectionMetadata
import re


class TestHTMLSectionParser:
    """Test suite for the HTMLSectionParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = HTMLSectionParser()
    
    def test_empty_html(self):
        """Test parsing empty HTML."""
        sections = self.parser.parse_template("")
        assert len(sections) == 0
        
        sections = self.parser.parse_template("   ")
        assert len(sections) == 0
    
    def test_simple_heading_sections(self):
        """Test parsing simple heading-based sections."""
        html = """
        <h1>Document Title</h1>
        <p>Introduction paragraph.</p>
        <h2>First Section</h2>
        <p>First section content.</p>
        <h2>Second Section</h2>
        <p>Second section content.</p>
        """
        
        sections = self.parser.parse_template(html)
        
        # Should identify 3 sections (h1, h2, h2)
        assert len(sections) == 3
        
        # Check section types
        assert all(section.section_type == SectionType.HEADING for section in sections)
        
        # Check section content
        assert "Document Title" in sections[0].html_content
        assert "Introduction paragraph" in sections[0].html_content
        assert "First Section" in sections[1].html_content
        assert "First section content" in sections[1].html_content
        assert "Second Section" in sections[2].html_content
        assert "Second section content" in sections[2].html_content
        
        # Check metadata
        assert sections[0].metadata.level == 1
        assert sections[1].metadata.level == 2
        assert sections[2].metadata.level == 2
        
        # Check hierarchy
        assert sections[0].parent_id is None
        assert sections[1].parent_id == sections[0].id
        assert sections[2].parent_id == sections[0].id
        assert sections[1].id in sections[0].children
        assert sections[2].id in sections[0].children
    
    def test_nested_heading_sections(self):
        """Test parsing nested heading sections."""
        html = """
        <h1>Document Title</h1>
        <p>Introduction paragraph.</p>
        <h2>First Section</h2>
        <p>First section content.</p>
        <h3>Subsection</h3>
        <p>Subsection content.</p>
        <h2>Second Section</h2>
        <p>Second section content.</p>
        """
        
        sections = self.parser.parse_template(html)
        
        # Should identify 4 sections (h1, h2, h3, h2)
        assert len(sections) == 4
        
        # Check hierarchy
        assert sections[0].parent_id is None
        assert sections[1].parent_id == sections[0].id
        assert sections[2].parent_id == sections[1].id
        assert sections[3].parent_id == sections[0].id
        assert sections[1].id in sections[0].children
        assert sections[2].id in sections[1].children
        assert sections[3].id in sections[0].children
    
    def test_table_sections(self):
        """Test parsing table sections."""
        html = """
        <h1>Document with Tables</h1>
        <p>Introduction paragraph.</p>
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Data 1</td><td>Data 2</td></tr>
        </table>
        <p>More content.</p>
        <table>
            <tr><td>Another table</td></tr>
        </table>
        """
        
        sections = self.parser.parse_template(html)
        
        # Should identify 3 sections (h1, table, table)
        assert len(sections) == 3
        
        # Check section types
        assert sections[0].section_type == SectionType.HEADING
        assert sections[1].section_type == SectionType.TABLE
        assert sections[2].section_type == SectionType.TABLE
        
        # Check table content
        assert "Header 1" in sections[1].html_content
        assert "Another table" in sections[2].html_content
        
        # Check hierarchy
        assert sections[1].parent_id == sections[0].id
        assert sections[2].parent_id == sections[0].id
    
    def test_list_sections(self):
        """Test parsing list sections."""
        html = """
        <h1>Document with Lists</h1>
        <p>Introduction paragraph.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <p>More content.</p>
        <ol>
            <li>Numbered item 1</li>
            <li>Numbered item 2</li>
        </ol>
        """
        
        sections = self.parser.parse_template(html)
        
        # Should identify 3 sections (h1, ul, ol)
        assert len(sections) == 3
        
        # Check section types
        assert sections[0].section_type == SectionType.HEADING
        assert sections[1].section_type == SectionType.LIST
        assert sections[2].section_type == SectionType.LIST
        
        # Check list content
        assert "Item 1" in sections[1].html_content
        assert "Numbered item" in sections[2].html_content
    
    def test_code_block_sections(self):
        """Test parsing code block sections."""
        html = """
        <h1>Document with Code</h1>
        <p>Introduction paragraph.</p>
        <pre><code>
        def hello_world():
            print("Hello, world!")
        </code></pre>
        <p>More content.</p>
        <pre>
            Another code block
        </pre>
        """
        
        sections = self.parser.parse_template(html)
        
        # Should identify 3 sections (h1, pre/code, pre)
        assert len(sections) == 3
        
        # Check section types
        assert sections[0].section_type == SectionType.HEADING
        assert sections[1].section_type == SectionType.CODE_BLOCK
        assert sections[2].section_type == SectionType.CODE_BLOCK
        
        # Check code content
        assert "hello_world" in sections[1].html_content
        assert "Another code block" in sections[2].html_content
    
    def test_paragraph_grouping(self):
        """Test grouping of adjacent paragraphs."""
        html = """
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
        
        <p>Third paragraph after a gap.</p>
        """
        
        sections = self.parser.parse_template(html)
        
        # Should identify 2 paragraph groups
        assert len(sections) == 2
        
        # Check section types
        assert sections[0].section_type == SectionType.PARAGRAPH
        assert sections[1].section_type == SectionType.PARAGRAPH
        
        # Check content
        assert "First paragraph" in sections[0].html_content
        assert "Second paragraph" in sections[0].html_content
        assert "Third paragraph" in sections[1].html_content
    
    def test_complex_document(self):
        """Test parsing a complex document with mixed content types."""
        html = """
        <h1>Complex Document</h1>
        <p>Introduction paragraph.</p>
        <h2>Section with Table</h2>
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Data 1</td><td>Data 2</td></tr>
        </table>
        <h2>Section with List</h2>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <h3>Subsection</h3>
        <p>Subsection content.</p>
        <pre><code>
        def hello_world():
            print("Hello, world!")
        </code></pre>
        <h2>Final Section</h2>
        <p>Final content.</p>
        """
        
        sections = self.parser.parse_template(html)
        
        # Should identify multiple sections
        assert len(sections) > 5
        
        # Check for different section types
        section_types = [section.section_type for section in sections]
        assert SectionType.HEADING in section_types
        assert SectionType.TABLE in section_types
        assert SectionType.LIST in section_types
        assert SectionType.CODE_BLOCK in section_types
        
        # Check hierarchy
        h1_sections = [s for s in sections if s.section_type == SectionType.HEADING and s.metadata.level == 1]
        h2_sections = [s for s in sections if s.section_type == SectionType.HEADING and s.metadata.level == 2]
        h3_sections = [s for s in sections if s.section_type == SectionType.HEADING and s.metadata.level == 3]
        
        assert len(h1_sections) == 1
        assert len(h2_sections) == 3
        assert len(h3_sections) == 1
        
        # All h2 sections should have h1 as parent
        for h2 in h2_sections:
            assert h2.parent_id == h1_sections[0].id
        
        # h3 section should have an h2 as parent
        assert h3_sections[0].parent_id in [h2.id for h2 in h2_sections]
    
    def test_section_metadata_extraction(self):
        """Test extraction of section metadata."""
        # Test heading metadata
        heading_html = "<h2 class='section-title important' id='section-1'>Section Title</h2><p>Content</p>"
        metadata = self.parser.extract_section_metadata(heading_html, SectionType.HEADING)
        
        assert metadata.level == 2
        assert metadata.tag_name == "h2"
        assert "section-title" in metadata.classes
        assert "important" in metadata.classes
        assert metadata.attributes.get("id") == "section-1"
        assert metadata.word_count >= 2  # At least "Section", "Title"
        
        # Test table metadata
        table_html = "<table class='data-table'><tr><td>Data</td></tr></table>"
        metadata = self.parser.extract_section_metadata(table_html, SectionType.TABLE)
        
        assert metadata.tag_name == "table"
        assert "data-table" in metadata.classes
        assert metadata.word_count == 1  # "Data"
        
        # Test list metadata
        list_html = "<ul class='feature-list'><li>Item 1</li><li>Item 2</li></ul>"
        metadata = self.parser.extract_section_metadata(list_html, SectionType.LIST)
        
        assert metadata.tag_name == "ul"
        assert "feature-list" in metadata.classes
        assert metadata.word_count == 4  # "Item", "1", "Item", "2"
    
    def test_html_cleaning(self):
        """Test HTML cleaning functionality."""
        html = """
        <h1>Document Title</h1>
        <!-- This is a comment -->
        <script>alert('test');</script>
        <style>.test { color: red; }</style>
        <p>Content paragraph.</p>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        self.parser._clean_html(soup)
        
        # Comments, scripts, and styles should be removed
        assert "<!-- This is a comment -->" not in str(soup)
        assert "<script>" not in str(soup)
        assert "<style>" not in str(soup)
        
        # Content should remain
        assert "<h1>Document Title</h1>" in str(soup)
        assert "<p>Content paragraph.</p>" in str(soup)
    
    def test_boundary_detection(self):
        """Test section boundary detection."""
        html = """
        <h1>Title</h1>
        <p>Intro</p>
        <h2>Section 1</h2>
        <p>Content 1</p>
        <h2>Section 2</h2>
        <p>Content 2</p>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        boundaries = self.parser.identify_section_boundaries(soup)
        
        # Should identify 3 boundaries (h1, h2, h2)
        assert len(boundaries) == 3
        
        # Check boundary types
        assert all(b.section_type == SectionType.HEADING for b in boundaries)
        
        # Check boundary levels
        assert boundaries[0].level == 1
        assert boundaries[1].level == 2
        assert boundaries[2].level == 2
        
        # Check start elements
        assert boundaries[0].start_element.name == "h1"
        assert boundaries[1].start_element.name == "h2"
        assert boundaries[2].start_element.name == "h2"
        
        # Check end elements
        assert boundaries[0].end_element is None  # Last h1, no end
        assert boundaries[1].end_element == boundaries[2].start_element  # h2 ends at next h2
        assert boundaries[2].end_element is None  # Last h2, no end 
    
    def test_nested_structures(self):
        """Test parsing deeply nested structures."""
        html = """
        <div class="container">
            <h1>Main Title</h1>
            <div class="content">
                <p>Introduction text.</p>
                <div class="section">
                    <h2>Nested Section</h2>
                    <ul>
                        <li>Nested item 1</li>
                        <li>Nested item 2
                            <ol>
                                <li>Sub-item 1</li>
                                <li>Sub-item 2</li>
                            </ol>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
        """
        
        sections = self.parser.parse_template(html)
        
        # Check that nested structures are properly identified
        assert len(sections) > 0
        
        # Verify heading section contains the nested content
        heading_sections = [s for s in sections if s.section_type == SectionType.HEADING]
        assert len(heading_sections) >= 2
        
        # Check that the nested list is identified
        list_sections = [s for s in sections if s.section_type == SectionType.LIST]
        assert len(list_sections) > 0
        
        # Verify content of nested list
        list_content = list_sections[0].html_content
        assert "Nested item" in list_content
        assert "Sub-item" in list_content
    
    def test_malformed_html(self):
        """Test parsing malformed HTML."""
        html = """
        <h1>Unclosed Heading
        <p>Paragraph with <strong>unclosed tag
        <div>
            <span>Nested unclosed span
        </div>
        <table>
            <tr><td>Cell 1</td><td>Cell 2</tr>
        </table>
        """
        
        # Should not raise exceptions
        sections = self.parser.parse_template(html)
        
        # Should still identify some sections
        assert len(sections) > 0
        
        # Check that BeautifulSoup has attempted to fix the HTML
        heading_sections = [s for s in sections if s.section_type == SectionType.HEADING]
        assert len(heading_sections) > 0
        assert "Unclosed Heading" in heading_sections[0].html_content
        
        # Check that the table was identified despite being malformed
        table_sections = [s for s in sections if s.section_type == SectionType.TABLE]
        assert len(table_sections) > 0
    
    def test_html_with_comments_and_scripts(self):
        """Test parsing HTML with comments and scripts."""
        html = """
        <h1>Document Title</h1>
        <!-- This comment should be removed -->
        <p>First paragraph.</p>
        <script>
            // This script should be removed
            document.getElementById("test").innerHTML = "Hello";
        </script>
        <h2>Section Title</h2>
        <style>
            /* This style should be removed */
            body { color: red; }
        </style>
        <p>Second paragraph.</p>
        """
        
        sections = self.parser.parse_template(html)
        
        # Check that comments, scripts, and styles are removed
        for section in sections:
            assert "<!--" not in section.html_content
            assert "<script>" not in section.html_content
            assert "<style>" not in section.html_content
            assert "document.getElementById" not in section.html_content
            assert "body { color: red; }" not in section.html_content
    
    def test_complex_table_structures(self):
        """Test parsing complex table structures."""
        html = """
        <h1>Table Test</h1>
        <table class="complex-table" id="data-table">
            <thead>
                <tr>
                    <th colspan="2">Header 1</th>
                    <th rowspan="2">Header 2</th>
                </tr>
                <tr>
                    <th>Subheader 1</th>
                    <th>Subheader 2</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Data 1</td>
                    <td>Data 2</td>
                    <td>Data 3</td>
                </tr>
                <tr>
                    <td>Data 4</td>
                    <td>Data 5</td>
                    <td>Data 6</td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="3">Footer</td>
                </tr>
            </tfoot>
        </table>
        """
        
        sections = self.parser.parse_template(html)
        
        # Check that the table is identified
        table_sections = [s for s in sections if s.section_type == SectionType.TABLE]
        assert len(table_sections) == 1
        
        # Check table metadata
        table_metadata = table_sections[0].metadata
        assert table_metadata.tag_name == "table"
        assert "complex-table" in table_metadata.classes
        assert table_metadata.attributes.get("id") == "data-table"
        
        # Check table content
        table_content = table_sections[0].html_content
        assert "Header 1" in table_content
        assert "Subheader" in table_content
        assert "Data 1" in table_content
        assert "Footer" in table_content
        
        # Check that colspan and rowspan attributes are preserved
        assert "colspan=\"2\"" in table_content
        assert "rowspan=\"2\"" in table_content
    
    def test_adjacent_paragraph_detection(self):
        """Test detection of adjacent paragraphs."""
        # Test adjacent paragraphs
        p1 = BeautifulSoup("<p>First paragraph</p>", "html.parser").p
        p2 = BeautifulSoup("<p>Second paragraph</p>", "html.parser").p
        
        # Create a document with adjacent paragraphs
        doc = BeautifulSoup("<div></div>", "html.parser")
        doc.div.append(p1)
        doc.div.append(p2)
        
        # Test the method
        assert self.parser._are_adjacent_paragraphs(p1, p2) == True
        
        # Test non-adjacent paragraphs
        p3 = BeautifulSoup("<p>Third paragraph</p>", "html.parser").p
        doc.div.append(BeautifulSoup("<div>Some content</div>", "html.parser").div)
        doc.div.append(p3)
        
        assert self.parser._are_adjacent_paragraphs(p2, p3) == False
    
    def test_complexity_score_calculation(self):
        """Test calculation of complexity score for HTML sections."""
        # Simple HTML
        simple_html = "<p>Simple paragraph.</p>"
        simple_soup = BeautifulSoup(simple_html, "html.parser")
        simple_score = self.parser._calculate_complexity_score(simple_soup)
        
        # Complex HTML
        complex_html = """
        <div class="container">
            <h2 id="title" class="heading">Complex Section</h2>
            <table>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><td>Data 1</td><td>Data 2</td></tr>
            </table>
            <ul>
                <li>Item 1</li>
                <li>Item 2
                    <ol>
                        <li>Subitem 1</li>
                        <li>Subitem 2</li>
                    </ol>
                </li>
            </ul>
        </div>
        """
        complex_soup = BeautifulSoup(complex_html, "html.parser")
        complex_score = self.parser._calculate_complexity_score(complex_soup)
        
        # Complex score should be higher than simple score
        assert complex_score > simple_score
        
        # Check that tables increase complexity significantly
        table_html = "<table><tr><td>Data</td></tr></table>"
        table_soup = BeautifulSoup(table_html, "html.parser")
        table_score = self.parser._calculate_complexity_score(table_soup)
        
        paragraph_html = "<p>A paragraph with similar length.</p>"
        paragraph_soup = BeautifulSoup(paragraph_html, "html.parser")
        paragraph_score = self.parser._calculate_complexity_score(paragraph_soup)
        
        assert table_score > paragraph_score
    
    def test_html_with_special_characters(self):
        """Test parsing HTML with special characters."""
        html = """
        <h1>Special &amp; Characters</h1>
        <p>This paragraph has &lt;tags&gt; inside text.</p>
        <p>This has unicode: &#x2713; &#8730; &copy; &euro;</p>
        <pre><code>if (x &lt; 10 &amp;&amp; y &gt; 20) { ... }</code></pre>
        """
        
        sections = self.parser.parse_template(html)
        
        # Check that special characters are preserved
        heading = [s for s in sections if s.section_type == SectionType.HEADING][0]
        assert "&amp;" in heading.html_content
        
        paragraphs = [s for s in sections if s.section_type == SectionType.PARAGRAPH]
        assert "&lt;tags&gt;" in paragraphs[0].html_content
        assert "&#x2713;" in paragraphs[1].html_content or "✓" in paragraphs[1].html_content
        
        code_blocks = [s for s in sections if s.section_type == SectionType.CODE_BLOCK]
        assert "&lt; 10 &amp;&amp;" in code_blocks[0].html_content
    
    def test_empty_elements(self):
        """Test parsing HTML with empty elements."""
        html = """
        <h1>Document with Empty Elements</h1>
        <p></p>
        <div></div>
        <span></span>
        <p>This is a non-empty paragraph.</p>
        <ul>
            <li></li>
            <li>Non-empty item</li>
        </ul>
        """
        
        sections = self.parser.parse_template(html)
        
        # Check that empty elements are handled properly
        heading = [s for s in sections if s.section_type == SectionType.HEADING][0]
        assert "Document with Empty Elements" in heading.html_content
        
        # Empty paragraphs should be removed during cleaning
        paragraphs = [s for s in sections if s.section_type == SectionType.PARAGRAPH]
        for p in paragraphs:
            assert "<p></p>" not in p.html_content
        
        # Check that non-empty content is preserved
        assert any("Non-empty paragraph" in s.html_content for s in sections)
        
        # Check that lists with some empty items are preserved
        lists = [s for s in sections if s.section_type == SectionType.LIST]
        assert len(lists) > 0
        assert "Non-empty item" in lists[0].html_content