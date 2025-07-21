import logging
from typing import Dict, Any
from backend.ai.html_parser import HTMLSectionParser
from backend.ai.content_generator import ContentGenerator
from backend.ai.models import WorkflowState, ValidationStatus, GeneratedSection

logger = logging.getLogger(__name__)

class ParseTemplateNode:
    """
    Node: Parses the HTML template into document sections.
    """
    def __init__(self):
        self.parser = HTMLSectionParser()

    def process(self, state: WorkflowState) -> WorkflowState:
        html = state["html_template"]
        sections = self.parser.parse_template(html)
        state["sections"] = sections
        state["total_sections"] = len(sections)
        logger.info(f"Parsed template into {len(sections)} sections.")
        return state

class GenerateSectionNode:
    """
    Node: Generates content for the current section using Gemini LLM.
    """
    def __init__(self, content_generator: ContentGenerator):
        self.generator = content_generator

    async def process(self, state: WorkflowState) -> WorkflowState:
        idx = state["current_section_index"]
        if idx >= len(state["sections"]):
            logger.warning("No more sections to generate.")
            return state
        section = state["sections"][idx]
        context = state["project_context"]
        generated = await self.generator.generate_section(section, context)
        state.setdefault("generated_sections", []).append(generated)
        logger.info(f"Generated section {section.id} (index {idx}).")
        return state

class ValidatorNode:
    """
    Node: Validates the generated section's HTML/content.
    """
    def process(self, state: WorkflowState) -> WorkflowState:
        idx = state["current_section_index"]
        if idx >= len(state["generated_sections"]):
            logger.warning("No generated section to validate.")
            return state
        generated: GeneratedSection = state["generated_sections"][idx]
        # Simple validation: check non-empty, valid HTML
        if generated.generated_html and "<" in generated.generated_html:
            generated.validation_status = ValidationStatus.VALID
            logger.info(f"Section {generated.section_id} validated as valid.")
        else:
            generated.validation_status = ValidationStatus.INVALID
            generated.error_message = "Generated content is empty or invalid."
            logger.warning(f"Section {generated.section_id} failed validation.")
        return state

class AssemblerNode:
    """
    Node: Assembles all generated sections into the final HTML document.
    """
    def process(self, state: WorkflowState) -> WorkflowState:
        generated_sections = state.get("generated_sections", [])
        # Concatenate all generated HTML in order
        final_html = "\n".join([g.generated_html for g in generated_sections if g.generated_html])
        state["final_html"] = final_html
        logger.info(f"Assembled final HTML document with {len(generated_sections)} sections.")
        return state

class ErrorHandlerNode:
    """
    Node: Handles errors and applies fallback logic.
    """
    def process(self, state: WorkflowState) -> WorkflowState:
        errors = []
        for g in state.get("generated_sections", []):
            if g.validation_status == ValidationStatus.INVALID:
                errors.append(f"Section {g.section_id}: {g.error_message}")
        state["errors"] = errors
        if errors:
            logger.error(f"Errors in generation: {errors}")
        return state

class DocumentGenerationWorkflow:
    """
    Orchestrates the document generation workflow using LangGraph-style nodes.
    Steps:
      1. Parse template into sections
      2. For each section: generate content, validate
      3. Assemble final HTML
      4. Handle errors
    """
    def __init__(self, content_generator: ContentGenerator = None):
        self.parse_node = ParseTemplateNode()
        self.content_generator = content_generator or ContentGenerator()
        self.generate_node = GenerateSectionNode(self.content_generator)
        self.validator_node = ValidatorNode()
        self.assembler_node = AssemblerNode()
        self.error_handler_node = ErrorHandlerNode()

    async def run(self, html_template: str, project_context) -> WorkflowState:
        """
        Run the document generation workflow.
        Args:
            html_template: The HTML template to parse and regenerate
            project_context: ProjectContext object with user input
        Returns:
            WorkflowState dict with all results and errors
        """
        state: WorkflowState = {
            "html_template": html_template,
            "project_context": project_context,
            "sections": [],
            "generated_sections": [],
            "final_html": "",
            "errors": [],
            "metadata": {},
            "current_section_index": 0,
            "total_sections": 0
        }
        # 1. Parse template
        state = self.parse_node.process(state)
        # 2. For each section: generate, validate
        for idx in range(state["total_sections"]):
            state["current_section_index"] = idx
            state = await self.generate_node.process(state)
            state = self.validator_node.process(state)
        # 3. Assemble final HTML
        state = self.assembler_node.process(state)
        # 4. Handle errors
        state = self.error_handler_node.process(state)
        logger.info("Document generation workflow complete.")
        return state