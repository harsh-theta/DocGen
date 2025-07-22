import asyncio
import httpx
import logging
from typing import List, Dict, Any, Optional
from backend.core.config import settings
from backend.ai.models import DocumentSection, GeneratedSection, ProjectContext, ValidationStatus
from backend.ai.project_analyzer import ProjectContextAnalyzer

logger = logging.getLogger(__name__)

class ContentGenerator:
    """
    Content generator for section-based document generation using Gemini LLM.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.DEFAULT_GENERATION_MODEL
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent".format(self.model)
        self.timeout = settings.AI_GENERATION_TIMEOUT
        self.max_retries = 3
        self.rate_limit = 5  # max concurrent requests
        self.semaphore = asyncio.Semaphore(self.rate_limit)

    def build_prompt(self, section: DocumentSection, context: ProjectContext) -> str:
        """
        Build a prompt for the LLM for a given section and project context.
        Includes project analysis instructions to generate custom values instead of copying reference data.
        Explicitly request valid HTML output only.
        """
        # Analyze project context to get project-specific metrics
        project_metrics = ProjectContextAnalyzer.analyze_project_scope(context)
        
        # Check if section contains tables that might need custom values
        contains_tables = "<table" in section.html_content
        
        base = (
            f"Rewrite the following document section using the new project context.\n\n"
            f"Original:\n{section.html_content}\n\n"
            f"Context:\nProject name: {context.project_name}\nProject description: {context.project_description}\n"
            f"User prompt:\n{context.prompt_text}\n"
        )
        
        # Add project metrics to help generate custom values
        base += (
            f"\nProject Analysis:\n"
            f"- Complexity Score: {project_metrics.complexity_score:.2f}\n"
            f"- Estimated Total Hours: {project_metrics.estimated_hours.get('total', 0)}\n"
            f"- Project Duration: {project_metrics.timeline_breakdown.get('duration', 'Unknown')}\n"
            f"- Required Resources: {', '.join(project_metrics.resource_requirements)}\n"
        )
        
        # Add specific instructions for tables and timelines
        if contains_tables:
            base += (
                f"\nTable Generation Instructions:\n"
                f"- DO NOT copy values from the original table\n"
                f"- Generate new, realistic values specific to this project\n"
                f"- Use the project metrics above to inform your values\n"
                f"- For timelines, use these phase timelines: {project_metrics.timeline_breakdown}\n"
                f"- For hour estimates, use these values: {project_metrics.estimated_hours}\n"
                f"- Maintain the same table structure but with project-specific data\n"
            )
        
        # Add any custom values that should be used
        if project_metrics.custom_values:
            base += f"\nCustom Values to Use:\n"
            for key, value in project_metrics.custom_values.items():
                base += f"- {key}: {value}\n"
        
        if context.json_overrides:
            base += f"\nOverrides:\n{context.json_overrides}\n"
        
        # Explicitly request valid HTML only
        base += ("\nReturn the result as valid HTML only. Do not use Markdown, do not use triple backticks, do not prefix with 'html'. ")
        base += ("If you need to use headings, use <h1>, <h2>, etc. If you need lists, use <ul>/<ol> and <li>. ")
        base += ("Do not include any code block markers or Markdown syntax.")
        return base

    def postprocess_output(self, output: str) -> str:
        """
        Post-process LLM output to remove Markdown artifacts and triple backticks.
        Convert Markdown headings to HTML if needed.
        """
        import re
        # Remove triple backticks and any 'html' after them
        output = re.sub(r"```(html)?", "", output)
        # Convert Markdown headings to HTML
        output = re.sub(r"^## (.+)$", r"<h2>\1</h2>", output, flags=re.MULTILINE)
        output = re.sub(r"^# (.+)$", r"<h1>\1</h1>", output, flags=re.MULTILINE)
        # Remove stray backticks
        output = output.replace("`", "")
        return output.strip()

    def validate_generated_content(self, section: DocumentSection, generated_html: str, context: ProjectContext) -> tuple[bool, Optional[str]]:
        """
        Validate that generated content is project-relevant and not copying reference data.
        
        Args:
            section: Original document section
            generated_html: Generated HTML content
            context: Project context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Use ProjectContextAnalyzer to validate content
        return ProjectContextAnalyzer.validate_generated_content(
            section.html_content, 
            generated_html, 
            context
        )
    
    async def generate_section(self, section: DocumentSection, context: ProjectContext) -> GeneratedSection:
        """
        Generate content for a single section using Gemini LLM.
        Returns a GeneratedSection with result or error.
        Includes validation to ensure project relevance.
        """
        prompt = self.build_prompt(section, context)
        # Use Gemini API key header
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        retries = 0
        error_message = None
        response_text = ""
        import time
        start_time = time.time()
        async with self.semaphore:
            while retries < self.max_retries:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        resp = await client.post(self.api_url, headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            # Gemini returns generated text in a nested structure
                            response_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if response_text:
                                # Post-process output
                                response_text = self.postprocess_output(response_text)
                                
                                # Validate the generated content
                                is_valid, validation_error = self.validate_generated_content(section, response_text, context)
                                
                                validation_status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
                                
                                # If content is valid or we've reached max retries, return the result
                                if is_valid or retries >= self.max_retries - 1:
                                    logger.info(f"Generated section {section.id} successfully. Validation: {validation_status}")
                                    return GeneratedSection(
                                        section_id=section.id,
                                        original_html=section.html_content,
                                        generated_html=response_text,
                                        generation_metadata={
                                            "model": self.model, 
                                            "status_code": resp.status_code,
                                            "validation_result": is_valid
                                        },
                                        validation_status=validation_status,
                                        error_message=validation_error,
                                        generation_time_ms=int((time.time() - start_time) * 1000)
                                    )
                                else:
                                    # If content is invalid and we have retries left, try again
                                    error_message = f"Content validation failed: {validation_error}"
                                    logger.warning(f"Section {section.id} validation failed: {validation_error}. Retrying.")
                            else:
                                error_message = "Empty response from Gemini API."
                        else:
                            error_message = f"Gemini API error: {resp.status_code} {resp.text}"
                    logger.warning(f"Retrying section {section.id} due to error: {error_message}")
                except Exception as e:
                    error_message = str(e)
                    logger.error(f"Exception during Gemini call: {e}")
                retries += 1
                await asyncio.sleep(1.5 * retries)  # Exponential backoff
        # If we reach here, all retries failed
        return GeneratedSection(
            section_id=section.id,
            original_html=section.html_content,
            generated_html="",
            generation_metadata={"model": self.model, "error": error_message},
            validation_status=ValidationStatus.INVALID,
            error_message=error_message,
            generation_time_ms=int((time.time() - start_time) * 1000)
        )

    async def generate_sections(self, sections: List[DocumentSection], context: ProjectContext) -> List[GeneratedSection]:
        """
        Generate content for a list of sections concurrently, respecting rate limits.
        """
        tasks = [self.generate_section(section, context) for section in sections]
        return await asyncio.gather(*tasks)
