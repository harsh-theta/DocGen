"""
HTML section parser for extracting document sections.

This module provides functionality to parse HTML documents into semantic sections
that can be processed independently by the AI document generation system.
"""

import re
import uuid
from typing import List, Dict, Any, Optional, Tuple, Set
from bs4 import BeautifulSoup, Tag, NavigableString, Comment
from dataclasses import dataclass
import logging

from .models import DocumentSection, SectionType, SectionMetadata

# Configure logger
logger = logging.getLogger(__name__)


@dataclass(unsafe_hash=True)
class SectionBoundary:
    """Represents a boundary between document sections."""
    start_element: Tag
    end_element: Optional[Tag]
    section_type: SectionType
    level: int = 0
    parent_boundary: Optional['SectionBoundary'] = None


class HTMLSectionParser:
    """
    Parser for extracting semantic sections from HTML documents.
    
    This class provides methods to parse HTML templates into distinct sections
    that can be processed independently by the AI generation system.
    """
    
    def __init__(self):
        """Initialize the HTML section parser."""
        self.heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        self.block_tags = ['div', 'section', 'article', 'aside', 'header', 'footer', 'nav']
        self.list_tags = ['ul', 'ol', 'dl']
        self.table_tags = ['table']
        self.code_tags = ['pre', 'code']
        self.remove_tags = ['script', 'style', 'iframe', 'noscript']
        self.max_paragraph_distance = 2  # Maximum number of elements between paragraphs to consider them adjacent
 
    def parse_template(self, html: str) -> List[DocumentSection]:
        """
        Parse an HTML template into a list of logical document sections.
        - Each <h2> and its following content up to the next <h2> (or end of doc) is a section.
        - Each table is its own section.
        - Content before the first <h2> is a single section.
        """
        if not html or not html.strip():
            return []
        soup = BeautifulSoup(html, 'html.parser')
        self._soup = soup
        sections = []
        order_index = 0
        # Find all h2s and tables
        all_h2s = soup.find_all('h2')
        all_tables = soup.find_all('table')
        # Mark table positions
        table_ids = {id(table): table for table in all_tables}
        # Section: content before first <h2>
        first_h2 = all_h2s[0] if all_h2s else None
        if first_h2:
            pre_h2_content = []
            for el in soup.body.contents if soup.body else soup.contents:
                if el == first_h2:
                    break
                if getattr(el, 'name', None) or str(el).strip():
                    pre_h2_content.append(str(el))
            if pre_h2_content:
                html_content = ''.join(pre_h2_content)
                metadata = self.extract_section_metadata(html_content, SectionType.PARAGRAPH)
                section = DocumentSection(
                    id=str(uuid.uuid4()),
                    html_content=html_content,
                    section_type=SectionType.PARAGRAPH,
                    metadata=metadata,
                    parent_id=None,
                    children=[],
                    order_index=order_index
                )
                sections.append(section)
                order_index += 1
        # Section: each <h2> and its following content up to next <h2>
        for idx, h2 in enumerate(all_h2s):
            section_content = [str(h2)]
            next_h2 = all_h2s[idx + 1] if idx + 1 < len(all_h2s) else None
            el = h2.next_sibling
            while el and el != next_h2:
                # If this is a table, make it its own section
                if getattr(el, 'name', None) == 'table':
                    # Add current section if it has content
                    if section_content:
                        html_content = ''.join(section_content)
                        metadata = self.extract_section_metadata(html_content, SectionType.PARAGRAPH)
                        section = DocumentSection(
                            id=str(uuid.uuid4()),
                            html_content=html_content,
                            section_type=SectionType.PARAGRAPH,
                            metadata=metadata,
                            parent_id=None,
                            children=[],
                            order_index=order_index
                        )
                        sections.append(section)
                        order_index += 1
                        section_content = []
                    # Add table as its own section
                    html_content = str(el)
                    metadata = self.extract_section_metadata(html_content, SectionType.TABLE)
                    section = DocumentSection(
                        id=str(uuid.uuid4()),
                        html_content=html_content,
                        section_type=SectionType.TABLE,
                        metadata=metadata,
                        parent_id=None,
                        children=[],
                        order_index=order_index
                    )
                    sections.append(section)
                    order_index += 1
                else:
                    if getattr(el, 'name', None) or str(el).strip():
                        section_content.append(str(el))
                el = el.next_sibling
            # Add the last section for this h2
            if section_content:
                html_content = ''.join(section_content)
                metadata = self.extract_section_metadata(html_content, SectionType.PARAGRAPH)
                section = DocumentSection(
                    id=str(uuid.uuid4()),
                    html_content=html_content,
                    section_type=SectionType.PARAGRAPH,
                    metadata=metadata,
                    parent_id=None,
                    children=[],
                    order_index=order_index
                )
                sections.append(section)
                order_index += 1
        # Section: any tables not already added
        for table in all_tables:
            if not any(str(table) in s.html_content for s in sections):
                html_content = str(table)
                metadata = self.extract_section_metadata(html_content, SectionType.TABLE)
                section = DocumentSection(
                    id=str(uuid.uuid4()),
                    html_content=html_content,
                    section_type=SectionType.TABLE,
                    metadata=metadata,
                    parent_id=None,
                    children=[],
                    order_index=order_index
                )
                sections.append(section)
                order_index += 1
        logger.info(f"Parsed HTML into {len(sections)} logical sections")
        return sections
        
    def _extract_section_content(self, boundary: SectionBoundary) -> str:
        """
        Extract the HTML content for a section based on its boundary.
        
        Args:
            boundary: The SectionBoundary defining the section
            
        Returns:
            HTML content as a string
        """
        start_element = boundary.start_element
        end_element = boundary.end_element
        
        # For self-contained elements like tables, lists, etc.
        if boundary.section_type in [SectionType.TABLE, SectionType.LIST, SectionType.CODE_BLOCK]:
            return str(start_element)
        
        # For heading-based sections, include all content until the end element
        content = [str(start_element)]
        current = start_element.next_sibling
        
        while current and current != end_element:
            if isinstance(current, Tag) or (isinstance(current, NavigableString) and current.strip()):
                content.append(str(current))
            current = current.next_sibling
        
        return ''.join(content)
        
    def _establish_section_hierarchy_from_boundaries(self, sections: List[DocumentSection], 
                                                   boundaries: List[SectionBoundary]) -> None:
        """
        Establish parent-child relationships between sections based on boundary hierarchy.
        
        Args:
            sections: List of DocumentSection objects
            boundaries: List of SectionBoundary objects used to create the sections
        """
        # Create a mapping from boundary to section
        boundary_to_section = {}
        for i, (section, boundary) in enumerate(zip(sections, boundaries)):
            boundary_to_section[boundary] = section
        
        # Set parent-child relationships based on boundary hierarchy
        for i, boundary in enumerate(boundaries):
            if boundary.parent_boundary and boundary.parent_boundary in boundary_to_section:
                parent_section = boundary_to_section[boundary.parent_boundary]
                child_section = sections[i]
                
                child_section.parent_id = parent_section.id
                parent_section.children.append(child_section.id)
    
    def identify_section_boundaries(self, soup: BeautifulSoup) -> List[SectionBoundary]:
        """
        Identify the boundaries between different sections in the document.
        
        Args:
            soup: BeautifulSoup object representing the HTML document
            
        Returns:
            A list of SectionBoundary objects
        """
        boundaries = []
        
        # First pass: identify heading-based sections
        heading_elements = []
        for tag_name in self.heading_tags:
            heading_elements.extend(soup.find_all(tag_name))
        
        # Sort headings by their position in the document
        heading_elements.sort(key=lambda x: self._get_element_position(soup, x))
        
        # Create boundaries for heading-based sections
        for i, heading in enumerate(heading_elements):
            level = int(heading.name[1])  # Extract heading level (h1 -> 1, h2 -> 2, etc.)
            
            # Find the end element (next heading of same or higher level, or None if last)
            end_element = None
            for next_heading in heading_elements[i+1:]:
                next_level = int(next_heading.name[1])
                if next_level <= level:
                    end_element = next_heading
                    break
            
            boundary = SectionBoundary(
                start_element=heading,
                end_element=end_element,
                section_type=SectionType.HEADING,
                level=level
            )
            boundaries.append(boundary)
        
        # Second pass: identify table-based sections that aren't within heading sections
        for table in soup.find_all('table'):
            # Skip if this table is already within a heading section
            if self._is_element_within_boundaries(table, boundaries):
                continue
                
            boundary = SectionBoundary(
                start_element=table,
                end_element=None,  # Tables are self-contained
                section_type=SectionType.TABLE,
                level=0
            )
            boundaries.append(boundary)
            
        # Third pass: identify list-based sections that aren't within other sections
        for list_tag in soup.find_all(self.list_tags):
            # Skip if this list is already within another section
            if self._is_element_within_boundaries(list_tag, boundaries):
                continue
                
            boundary = SectionBoundary(
                start_element=list_tag,
                end_element=None,  # Lists are self-contained
                section_type=SectionType.LIST,
                level=0
            )
            boundaries.append(boundary)
            
        # Fourth pass: identify code blocks that aren't within other sections
        for tag in self.code_tags:
            for code_block in soup.find_all(tag):
                # Skip if this code block is already within another section
                if self._is_element_within_boundaries(code_block, boundaries):
                    continue
                    
                boundary = SectionBoundary(
                    start_element=code_block,
                    end_element=None,  # Code blocks are self-contained
                    section_type=SectionType.CODE_BLOCK,
                    level=0
                )
                boundaries.append(boundary)
                
        # Fifth pass: identify paragraph groups
        self._identify_paragraph_groups(soup, boundaries)
        
        # Sort boundaries by position in document
        boundaries.sort(key=lambda b: self._get_element_position(soup, b.start_element))
        
        # Establish parent-child relationships between boundaries
        self._establish_boundary_hierarchy(boundaries)
        
        return boundaries
   
    def extract_section_metadata(self, section_html: str, section_type: SectionType) -> SectionMetadata:
        """
        Extract metadata from a section's HTML content.
        
        Args:
            section_html: The HTML content of the section
            section_type: The type of the section
            
        Returns:
            A SectionMetadata object with information about the section
        """
        soup = BeautifulSoup(section_html, 'html.parser')
        
        # Get the main tag name
        main_tag = None
        if section_type == SectionType.HEADING:
            for tag in self.heading_tags:
                if soup.find(tag):
                    main_tag = tag
                    break
        elif section_type == SectionType.TABLE:
            main_tag = 'table'
        elif section_type == SectionType.LIST:
            for tag in self.list_tags:
                if soup.find(tag):
                    main_tag = tag
                    break
        elif section_type == SectionType.CODE_BLOCK:
            for tag in self.code_tags:
                if soup.find(tag):
                    main_tag = tag
                    break
        else:
            main_tag = soup.find().name if soup.find() else 'div'
        
        # Get the level for headings
        level = 0
        if section_type == SectionType.HEADING and main_tag:
            level = int(main_tag[1]) if len(main_tag) > 1 else 0
        
        # Get classes and attributes from the main element
        classes = []
        attributes = {}
        
        main_element = soup.find(main_tag) if main_tag else None
        if main_element and hasattr(main_element, 'attrs'):
            classes = main_element.get('class', [])
            attributes = {k: v for k, v in main_element.attrs.items() if k != 'class'}
        
        # Calculate word count
        text = soup.get_text()
        word_count = len(re.findall(r'\w+', text))
        
        # Calculate complexity score (simple heuristic based on HTML structure)
        complexity_score = self._calculate_complexity_score(soup)
        
        return SectionMetadata(
            level=level,
            tag_name=main_tag or 'div',
            classes=classes if isinstance(classes, list) else [classes],
            attributes=attributes,
            word_count=word_count,
            complexity_score=complexity_score
        )    

    def _establish_section_hierarchy(self, sections: List[DocumentSection]) -> None:
        """
        Establish parent-child relationships between sections based on heading levels.
        
        Args:
            sections: List of DocumentSection objects
        """
        # Sort sections by order_index to ensure proper traversal
        sections.sort(key=lambda x: x.order_index)
        
        # Create a map of section IDs to their indices
        section_map = {section.id: i for i, section in enumerate(sections)}
        
        # Stack to keep track of potential parent sections
        # Each entry is (section_id, heading_level)
        parent_stack = []
        
        for section in sections:
            if section.section_type == SectionType.HEADING:
                current_level = section.metadata.level
                
                # Pop from stack until we find a potential parent (lower heading level)
                while parent_stack and parent_stack[-1][1] >= current_level:
                    parent_stack.pop()
                
                # If we have a potential parent, establish the relationship
                if parent_stack:
                    parent_id = parent_stack[-1][0]
                    section.parent_id = parent_id
                    parent_idx = section_map[parent_id]
                    sections[parent_idx].children.append(section.id)
                
                # Add current section to the stack as a potential parent for future sections
                parent_stack.append((section.id, current_level))
            else:
                # For non-heading sections, find the closest heading as parent
                closest_heading = None
                
                for i in range(section.order_index - 1, -1, -1):
                    if i < len(sections) and sections[i].section_type == SectionType.HEADING:
                        closest_heading = sections[i]
                        break
                
                if closest_heading:
                    section.parent_id = closest_heading.id
                    closest_heading.children.append(section.id)
    
    def _is_element_in_sections(self, element: Tag, sections: List[DocumentSection]) -> bool:
        """
        Check if an element is already included in any of the existing sections.
        
        Args:
            element: The element to check
            sections: List of existing sections
            
        Returns:
            True if the element is in any section, False otherwise
        """
        element_str = str(element)
        
        for section in sections:
            if element_str in section.html_content:
                return True
        
        return False
        
    def _clean_html(self, soup: BeautifulSoup) -> None:
        """
        Clean the HTML by removing unwanted elements.
        
        Args:
            soup: BeautifulSoup object to clean
        """
        # Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove script, style, and other unwanted tags
        for tag in self.remove_tags:
            for element in soup.find_all(tag):
                element.extract()
                
        # Remove empty tags (except for certain elements like br, hr)
        for element in soup.find_all():
            if element.name not in ['br', 'hr', 'img', 'input'] and not element.contents and not element.string:
                element.extract()
                
        # Remove excessive whitespace in text nodes
        for text in soup.find_all(text=True):
            if isinstance(text, NavigableString) and not isinstance(text, Comment):
                text.replace_with(re.sub(r'\s+', ' ', text.string))
                
    def _calculate_complexity_score(self, soup: BeautifulSoup) -> float:
        """
        Calculate a complexity score for an HTML section.
        
        The score is based on:
        - Number of nested elements
        - Presence of tables, lists, and other complex structures
        - Number of attributes
        - Total content length
        
        Args:
            soup: BeautifulSoup object representing the HTML section
            
        Returns:
            A float representing the complexity (higher = more complex)
        """
        # Base score
        score = 1.0
        
        # Count elements
        elements = soup.find_all()
        element_count = len(elements)
        score += element_count * 0.1
        
        # Check for complex structures
        tables = soup.find_all('table')
        score += len(tables) * 2.0
        
        lists = soup.find_all(['ul', 'ol', 'dl'])
        score += len(lists) * 1.5
        
        # Count attributes
        attr_count = sum(len(el.attrs) for el in elements if hasattr(el, 'attrs'))
        score += attr_count * 0.2
        
        # Calculate nesting depth
        max_depth = 0
        for element in elements:
            depth = 0
            parent = element.parent
            while parent and parent.name != '[document]':
                depth += 1
                parent = parent.parent
            max_depth = max(max_depth, depth)
        
        score += max_depth * 0.5
        
        # Content length factor
        content_length = len(soup.get_text())
        score += content_length * 0.001
        
        return score
        
    def _are_adjacent_paragraphs(self, p1: Tag, p2: Tag) -> bool:
        """
        Determine if two paragraph elements are adjacent in the document.
        
        Two paragraphs are considered adjacent if:
        - They are direct siblings with no significant content between them
        - They are separated by at most self.max_paragraph_distance elements
        
        Args:
            p1: First paragraph element
            p2: Second paragraph element
            
        Returns:
            True if paragraphs are adjacent, False otherwise
        """
        # Check if they're direct siblings
        current = p1.next_sibling
        distance = 0
        
        while current and distance <= self.max_paragraph_distance:
            if current == p2:
                return True
                
            # Count only significant elements
            if isinstance(current, Tag) and current.name not in ['br', 'hr']:
                distance += 1
            elif isinstance(current, NavigableString) and current.strip():
                # If there's significant text between paragraphs, they're not adjacent
                return False
                
            current = current.next_sibling
            
        return False
        
    def _get_element_position(self, soup: BeautifulSoup, element: Tag) -> int:
        """
        Get the position of an element in the document.
        
        Args:
            soup: BeautifulSoup object representing the document
            element: The element to find the position of
            
        Returns:
            An integer representing the element's position
        """
        if soup is None:
            soup = getattr(self, '_soup', None)
        if soup is None:
            return -1
        # Get all elements in the document
        all_elements = soup.find_all()
        
        # Find the position of the target element
        for i, el in enumerate(all_elements):
            if el is element:
                return i
                
        # Element not found
        return -1
        
    def _is_element_within_boundaries(self, element: Tag, boundaries: List[SectionBoundary]) -> bool:
        """
        Check if an element is within any of the existing section boundaries.
        
        Args:
            element: The element to check
            boundaries: List of section boundaries
            
        Returns:
            True if the element is within any boundary, False otherwise
        """
        for boundary in boundaries:
            # Check if element is the same as or after the start element
            if element is boundary.start_element:
                return True
                
            # Check if element is between start and end elements
            if boundary.end_element is None:
                # For self-contained elements like tables, check if element is a child
                if element in boundary.start_element.find_all():
                    return True
            else:
                # For sections with start and end elements, check position
                start_pos = self._get_element_position(element.parent, boundary.start_element)
                end_pos = self._get_element_position(element.parent, boundary.end_element)
                elem_pos = self._get_element_position(element.parent, element)
                
                if start_pos <= elem_pos < end_pos:
                    return True
                    
        return False
        
    def _identify_paragraph_groups(self, soup: BeautifulSoup, boundaries: List[SectionBoundary]) -> None:
        """
        Identify groups of paragraphs that should form their own sections.
        
        Args:
            soup: BeautifulSoup object representing the document
            boundaries: List of section boundaries to update
        """
        paragraphs = soup.find_all('p')
        current_group = []
        
        for p in paragraphs:
            # Skip if this paragraph is already within a boundary
            if self._is_element_within_boundaries(p, boundaries):
                continue
                
            if current_group and not self._are_adjacent_paragraphs(current_group[-1], p):
                # Start a new group if paragraphs aren't adjacent
                if current_group:
                    # Create a boundary for this paragraph group
                    boundary = SectionBoundary(
                        start_element=current_group[0],
                        end_element=current_group[-1].next_sibling,  # End at the element after the last paragraph
                        section_type=SectionType.PARAGRAPH,
                        level=0
                    )
                    boundaries.append(boundary)
                    
                current_group = [p]
            else:
                current_group.append(p)
        
        # Add the last paragraph group if it exists
        if current_group:
            boundary = SectionBoundary(
                start_element=current_group[0],
                end_element=None,  # No specific end element for the last group
                section_type=SectionType.PARAGRAPH,
                level=0
            )
            boundaries.append(boundary)
            
    def _establish_boundary_hierarchy(self, boundaries: List[SectionBoundary]) -> None:
        """
        Establish parent-child relationships between section boundaries.
        
        Args:
            boundaries: List of SectionBoundary objects
        """
        # First, handle heading-based hierarchy
        heading_boundaries = [b for b in boundaries if b.section_type == SectionType.HEADING]
        
        # Sort by level (h1, h2, etc.) and then by position
        heading_boundaries.sort(key=lambda b: (b.level, self._get_element_position(self._soup, b.start_element)))
        
        # Stack to keep track of potential parent boundaries
        # Each entry is a boundary
        parent_stack = []
        
        for boundary in heading_boundaries:
            current_level = boundary.level
            
            # Pop from stack until we find a potential parent (lower heading level)
            while parent_stack and parent_stack[-1].level >= current_level:
                parent_stack.pop()
            
            # If we have a potential parent, establish the relationship
            if parent_stack:
                boundary.parent_boundary = parent_stack[-1]
            
            # Add current boundary to the stack as a potential parent
            parent_stack.append(boundary)
        
        # Now handle non-heading sections
        for boundary in boundaries:
            if boundary.section_type != SectionType.HEADING and not boundary.parent_boundary:
                # Find the closest heading boundary that contains this element
                for heading_boundary in heading_boundaries:
                    # Check if this element is within the heading boundary
                    if self._is_element_between(boundary.start_element, 
                                               heading_boundary.start_element, 
                                               heading_boundary.end_element):
                        boundary.parent_boundary = heading_boundary
                        break
                        
    def _is_element_between(self, element: Tag, start_element: Tag, end_element: Optional[Tag]) -> bool:
        """
        Check if an element is between a start and end element in the document.
        
        Args:
            element: The element to check
            start_element: The start element of the range
            end_element: The end element of the range (or None if no specific end)
            
        Returns:
            True if the element is between start and end, False otherwise
        """
        if element is start_element:
            return True
            
        if not end_element:
            # If no end element, check if element is a descendant of start_element
            return element in start_element.find_all()
            
        # Get the common parent of all elements
        common_parent = self._find_common_parent(element, start_element, end_element)
        if not common_parent:
            return False
            
        # Get positions within the common parent
        all_elements = list(common_parent.find_all())
        
        try:
            elem_pos = all_elements.index(element)
            start_pos = all_elements.index(start_element)
            end_pos = all_elements.index(end_element)
            
            return start_pos <= elem_pos < end_pos
        except ValueError:
            # Element not found in the common parent
            return False
            
    def _find_common_parent(self, *elements: Tag) -> Optional[Tag]:
        """
        Find the common parent of multiple elements.
        
        Args:
            *elements: Variable number of Tag objects
            
        Returns:
            The common parent Tag, or None if no common parent exists
        """
        if not elements:
            return None
            
        # Get all parents for the first element
        first_element = elements[0]
        first_parents = [first_element]
        parent = first_element.parent
        
        while parent:
            first_parents.append(parent)
            parent = parent.parent
            
        # Check each parent against all other elements
        for parent in reversed(first_parents):  # Start from the highest level parent
            is_common = True
            
            for element in elements[1:]:
                current = element
                found = False
                
                # Check if this parent contains the element
                while current and not found:
                    if current is parent:
                        found = True
                    current = current.parent
                    
                if not found:
                    is_common = False
                    break
                    
            if is_common:
                return parent
                
        return None