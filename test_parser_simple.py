#!/usr/bin/env python3

import sys
sys.path.append('backend')

from backend.ai.html_parser import HTMLSectionParser
from backend.ai.models import SectionType

def test_simple_case():
    parser = HTMLSectionParser()
    
    # Test simple heading case
    html = """
    <h1>Document Title</h1>
    <p>Introduction paragraph.</p>
    <h2>First Section</h2>
    <p>First section content.</p>
    <h2>Second Section</h2>
    <p>Second section content.</p>
    """
    
    try:
        sections = parser.parse_template(html)
        print(f"Generated {len(sections)} sections")
        
        for i, section in enumerate(sections):
            print(f"Section {i}: {section.section_type.value} - {section.metadata.level if hasattr(section.metadata, 'level') else 'N/A'}")
            print(f"  Content preview: {section.html_content[:100]}...")
            print()
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_case()