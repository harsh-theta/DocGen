"""
Project context analyzer for generating project-specific data.

This module provides functionality to analyze project context and generate
realistic timelines, hours, and other project-specific data instead of
copying reference document data.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from backend.ai.models import ProjectContext

logger = logging.getLogger(__name__)

@dataclass
class ProjectMetrics:
    """Metrics and calculated values for a project."""
    complexity_score: float
    estimated_hours: Dict[str, int]
    timeline_breakdown: Dict[str, str]
    resource_requirements: List[str]
    custom_values: Dict[str, Any]


class ProjectContextAnalyzer:
    """
    Analyzes project context to generate realistic project-specific data
    like timelines, hours, and resource requirements.
    """
    
    # Complexity factors for different project types
    COMPLEXITY_FACTORS = {
        "web": 1.0,
        "mobile": 1.2,
        "desktop": 1.1,
        "api": 0.9,
        "data": 1.3,
        "ml": 1.5,
        "blockchain": 1.6,
        "iot": 1.4,
        "game": 1.3,
        "enterprise": 1.4
    }
    
    # Base hours for common project phases
    BASE_HOURS = {
        "requirements": 20,
        "design": 30,
        "development": 100,
        "testing": 40,
        "deployment": 15,
        "documentation": 10
    }
    
    # Timeline factors (in weeks)
    TIMELINE_FACTORS = {
        "small": 0.5,
        "medium": 1.0,
        "large": 2.0,
        "enterprise": 3.0
    }
    
    @classmethod
    def analyze_project_scope(cls, context: ProjectContext) -> ProjectMetrics:
        """
        Analyze project scope and generate project-specific metrics.
        
        Args:
            context: The project context containing project details
            
        Returns:
            ProjectMetrics with calculated values
        """
        # Calculate complexity score based on project description
        complexity_score = cls._calculate_complexity_score(context)
        
        # Generate estimated hours for different project phases
        estimated_hours = cls._calculate_estimated_hours(context, complexity_score)
        
        # Generate timeline breakdown
        timeline_breakdown = cls._calculate_timeline(context, estimated_hours)
        
        # Determine resource requirements
        resource_requirements = cls._determine_resources(context, complexity_score)
        
        # Generate custom values for tables and other data
        custom_values = cls._generate_custom_values(context, complexity_score, estimated_hours)
        
        return ProjectMetrics(
            complexity_score=complexity_score,
            estimated_hours=estimated_hours,
            timeline_breakdown=timeline_breakdown,
            resource_requirements=resource_requirements,
            custom_values=custom_values
        )
    
    @classmethod
    def _calculate_complexity_score(cls, context: ProjectContext) -> float:
        """Calculate project complexity score based on description and overrides."""
        base_score = 1.0
        description = context.project_description.lower()
        
        # Check for project type indicators in description
        for project_type, factor in cls.COMPLEXITY_FACTORS.items():
            if project_type in description:
                base_score *= factor
        
        # Check for complexity indicators in description
        if any(word in description for word in ["complex", "complicated", "advanced", "sophisticated"]):
            base_score *= 1.3
        elif any(word in description for word in ["simple", "basic", "straightforward"]):
            base_score *= 0.7
        
        # Check for scale indicators
        if any(word in description for word in ["large", "enterprise", "extensive"]):
            base_score *= 1.4
        elif any(word in description for word in ["small", "minimal", "prototype"]):
            base_score *= 0.6
        
        # Apply any explicit complexity override from json_overrides
        if "complexity" in context.json_overrides:
            try:
                override = float(context.json_overrides["complexity"])
                base_score = override
            except (ValueError, TypeError):
                pass
        
        # Ensure score is within reasonable bounds
        return max(0.5, min(3.0, base_score))
    
    @classmethod
    def _calculate_estimated_hours(cls, context: ProjectContext, complexity_score: float) -> Dict[str, int]:
        """Calculate estimated hours for different project phases."""
        result = {}
        
        # Apply complexity score to base hours
        for phase, base_hours in cls.BASE_HOURS.items():
            # Calculate hours with complexity factor and some randomness
            hours = int(base_hours * complexity_score * (0.9 + 0.2 * (hash(context.project_name + phase) % 100) / 100))
            result[phase] = hours
        
        # Apply any explicit hour overrides from json_overrides
        if "hours" in context.json_overrides and isinstance(context.json_overrides["hours"], dict):
            for phase, hours in context.json_overrides["hours"].items():
                try:
                    result[phase] = int(hours)
                except (ValueError, TypeError):
                    pass
        
        # Add total hours
        result["total"] = sum(result.values())
        
        return result
    
    @classmethod
    def _calculate_timeline(cls, context: ProjectContext, estimated_hours: Dict[str, int]) -> Dict[str, str]:
        """Calculate timeline breakdown for the project."""
        result = {}
        
        # Determine project size from total hours
        total_hours = estimated_hours.get("total", sum(estimated_hours.values()))
        project_size = "small"
        if total_hours > 500:
            project_size = "enterprise"
        elif total_hours > 300:
            project_size = "large"
        elif total_hours > 150:
            project_size = "medium"
        
        # Get timeline factor
        timeline_factor = cls.TIMELINE_FACTORS.get(project_size, 1.0)
        
        # Calculate weeks for each phase
        current_week = 1
        for phase, hours in estimated_hours.items():
            if phase == "total":
                continue
                
            # Calculate weeks needed for this phase
            phase_weeks = max(1, int(hours / 40 * timeline_factor))
            
            # Format as "Week X - Week Y"
            end_week = current_week + phase_weeks - 1
            result[phase] = f"Week {current_week} - Week {end_week}"
            current_week = end_week + 1
        
        # Add project duration
        result["duration"] = f"{current_week - 1} weeks"
        
        # Apply any explicit timeline overrides from json_overrides
        if "timeline" in context.json_overrides and isinstance(context.json_overrides["timeline"], dict):
            for phase, timeline in context.json_overrides["timeline"].items():
                result[phase] = timeline
        
        return result
    
    @classmethod
    def _determine_resources(cls, context: ProjectContext, complexity_score: float) -> List[str]:
        """Determine required resources based on project context."""
        resources = ["Project Manager"]
        description = context.project_description.lower()
        
        # Add developers based on complexity
        dev_count = max(1, int(complexity_score * 2))
        resources.append(f"{dev_count} Developers")
        
        # Add designers if UI/UX is mentioned
        if any(term in description for term in ["ui", "ux", "user interface", "user experience", "frontend", "front-end"]):
            resources.append("UI/UX Designer")
        
        # Add QA based on complexity
        if complexity_score > 1.0:
            qa_count = max(1, int(complexity_score))
            resources.append(f"{qa_count} QA Engineers")
        
        # Add DevOps if relevant
        if any(term in description for term in ["devops", "ci/cd", "deployment", "cloud", "infrastructure"]):
            resources.append("DevOps Engineer")
        
        # Add data specialists if relevant
        if any(term in description for term in ["data", "analytics", "database", "sql", "nosql"]):
            resources.append("Data Engineer")
        
        # Add ML specialists if relevant
        if any(term in description for term in ["ml", "ai", "machine learning", "artificial intelligence"]):
            resources.append("ML Engineer")
        
        # Apply any explicit resource overrides from json_overrides
        if "resources" in context.json_overrides and isinstance(context.json_overrides["resources"], list):
            return context.json_overrides["resources"]
        
        return resources
    
    @classmethod
    def _generate_custom_values(cls, context: ProjectContext, complexity_score: float, 
                               estimated_hours: Dict[str, int]) -> Dict[str, Any]:
        """Generate custom values for tables and other data points."""
        custom_values = {}
        
        # Generate cost estimates
        hourly_rate = 100  # Default hourly rate
        if "hourly_rate" in context.json_overrides:
            try:
                hourly_rate = float(context.json_overrides["hourly_rate"])
            except (ValueError, TypeError):
                pass
        
        total_hours = estimated_hours.get("total", sum(v for k, v in estimated_hours.items() if k != "total"))
        custom_values["cost_estimate"] = int(total_hours * hourly_rate)
        
        # Generate risk levels
        risk_level = "Medium"
        if complexity_score > 2.0:
            risk_level = "High"
        elif complexity_score < 1.0:
            risk_level = "Low"
        custom_values["risk_level"] = risk_level
        
        # Generate milestone dates
        import datetime
        today = datetime.date.today()
        
        milestones = {}
        current_date = today
        for phase, timeline in cls._calculate_timeline(context, estimated_hours).items():
            if phase == "duration":
                continue
                
            # Extract weeks from timeline string
            match = re.search(r"Week (\d+) - Week (\d+)", timeline)
            if match:
                end_week = int(match.group(2))
                # Calculate end date for this phase
                end_date = today + datetime.timedelta(weeks=end_week)
                milestones[phase] = end_date.strftime("%Y-%m-%d")
        
        custom_values["milestones"] = milestones
        
        # Add any explicit custom values from json_overrides
        if "custom" in context.json_overrides and isinstance(context.json_overrides["custom"], dict):
            for key, value in context.json_overrides["custom"].items():
                custom_values[key] = value
        
        return custom_values
    
    @classmethod
    def extract_table_structure(cls, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract table structure from HTML content to analyze and generate custom data.
        
        Args:
            html_content: HTML content containing tables
            
        Returns:
            List of dictionaries representing tables with their structure
        """
        tables = []
        
        # Simple regex-based table extraction
        table_pattern = re.compile(r'<table[^>]*>(.*?)</table>', re.DOTALL)
        header_pattern = re.compile(r'<th[^>]*>(.*?)</th>', re.DOTALL)
        row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
        cell_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)
        
        for table_match in table_pattern.finditer(html_content):
            table_html = table_match.group(1)
            table_data = {"headers": [], "rows": []}
            
            # Extract headers
            for header_match in header_pattern.finditer(table_html):
                header_text = cls._clean_html(header_match.group(1))
                table_data["headers"].append(header_text)
            
            # Extract rows
            for row_match in row_pattern.finditer(table_html):
                row_html = row_match.group(1)
                row_data = []
                
                # Skip if this row contains headers
                if "<th" in row_html:
                    continue
                    
                # Extract cells
                for cell_match in cell_pattern.finditer(row_html):
                    cell_text = cls._clean_html(cell_match.group(1))
                    row_data.append(cell_text)
                
                if row_data:
                    table_data["rows"].append(row_data)
            
            tables.append(table_data)
        
        return tables
    
    @staticmethod
    def _clean_html(html: str) -> str:
        """Remove HTML tags and clean up text."""
        # Simple tag removal
        text = re.sub(r'<[^>]+>', '', html)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    @classmethod
    def validate_generated_content(cls, original_html: str, generated_html: str, 
                                  context: ProjectContext) -> Tuple[bool, Optional[str]]:
        """
        Validate that generated content is project-relevant and not copying reference data.
        
        Args:
            original_html: Original HTML content
            generated_html: Generated HTML content
            context: Project context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Extract project-specific terms
        project_terms = set(context.project_name.lower().split())
        project_terms.update(context.project_description.lower().split())
        
        # Check if project name is included
        if context.project_name.lower() not in generated_html.lower():
            return False, "Generated content does not include project name"
        
        # Extract tables from original and generated content
        original_tables = cls.extract_table_structure(original_html)
        generated_tables = cls.extract_table_structure(generated_html)
        
        # If we have tables, check that values are different
        if original_tables and generated_tables:
            # Check if tables have the same structure but different values
            for orig_table, gen_table in zip(original_tables, generated_tables):
                if orig_table["headers"] == gen_table["headers"]:
                    # Check if all rows are identical (direct copying)
                    identical_rows = 0
                    for orig_row in orig_table["rows"]:
                        if orig_row in gen_table["rows"]:
                            identical_rows += 1
                    
                    # If more than 50% of rows are identical, likely copying
                    if identical_rows > len(orig_table["rows"]) * 0.5:
                        return False, "Generated content appears to copy reference data"
        
        return True, None