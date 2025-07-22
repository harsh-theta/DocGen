"""
Unit tests for the ProjectContextAnalyzer class.
"""

import pytest
from backend.ai.project_analyzer import ProjectContextAnalyzer, ProjectMetrics
from backend.ai.models import ProjectContext


class TestProjectContextAnalyzer:
    """Test suite for ProjectContextAnalyzer."""

    def test_analyze_project_scope(self):
        """Test that analyze_project_scope returns valid ProjectMetrics."""
        context = ProjectContext(
            project_name="Test Project",
            project_description="A medium complexity web application",
            prompt_text="Create a project plan for a web application",
            json_overrides={},
            strict_vars={}
        )
        
        metrics = ProjectContextAnalyzer.analyze_project_scope(context)
        
        # Verify the returned object is a ProjectMetrics instance
        assert isinstance(metrics, ProjectMetrics)
        
        # Verify the metrics have expected fields
        assert isinstance(metrics.complexity_score, float)
        assert isinstance(metrics.estimated_hours, dict)
        assert isinstance(metrics.timeline_breakdown, dict)
        assert isinstance(metrics.resource_requirements, list)
        assert isinstance(metrics.custom_values, dict)
        
        # Verify complexity score is within expected range
        assert 0.5 <= metrics.complexity_score <= 3.0
        
        # Verify estimated hours contains expected phases
        assert "requirements" in metrics.estimated_hours
        assert "development" in metrics.estimated_hours
        assert "total" in metrics.estimated_hours
        
        # Verify timeline breakdown contains expected phases
        assert "requirements" in metrics.timeline_breakdown
        assert "development" in metrics.timeline_breakdown
        assert "duration" in metrics.timeline_breakdown
        
        # Verify resource requirements are not empty
        assert len(metrics.resource_requirements) > 0
    
    def test_complexity_calculation(self):
        """Test that complexity calculation responds to project description."""
        # Test with a simple project
        simple_context = ProjectContext(
            project_name="Simple App",
            project_description="A simple, basic web application with minimal features",
            prompt_text="Create a simple app",
            json_overrides={},
            strict_vars={}
        )
        
        # Test with a complex project
        complex_context = ProjectContext(
            project_name="Enterprise System",
            project_description="A complex, large-scale enterprise system with ML components",
            prompt_text="Create an enterprise system",
            json_overrides={},
            strict_vars={}
        )
        
        simple_metrics = ProjectContextAnalyzer.analyze_project_scope(simple_context)
        complex_metrics = ProjectContextAnalyzer.analyze_project_scope(complex_context)
        
        # Complex project should have higher complexity score
        assert complex_metrics.complexity_score > simple_metrics.complexity_score
        
        # Complex project should have more estimated hours
        assert complex_metrics.estimated_hours["total"] > simple_metrics.estimated_hours["total"]
    
    def test_json_overrides(self):
        """Test that json_overrides are applied correctly."""
        context = ProjectContext(
            project_name="Override Test",
            project_description="Testing json overrides",
            prompt_text="Test overrides",
            json_overrides={
                "complexity": 2.5,
                "hours": {"development": 200},
                "timeline": {"development": "Week 3 - Week 8"},
                "resources": ["Custom Team", "5 Developers"]
            },
            strict_vars={}
        )
        
        metrics = ProjectContextAnalyzer.analyze_project_scope(context)
        
        # Verify overrides were applied
        assert metrics.complexity_score == 2.5
        assert metrics.estimated_hours["development"] == 200
        assert metrics.timeline_breakdown["development"] == "Week 3 - Week 8"
        assert "Custom Team" in metrics.resource_requirements
        assert "5 Developers" in metrics.resource_requirements
    
    def test_validate_generated_content(self):
        """Test content validation functionality."""
        context = ProjectContext(
            project_name="Validation Test",
            project_description="Testing content validation",
            prompt_text="Test validation",
            json_overrides={},
            strict_vars={}
        )
        
        # Test with content that includes project name
        valid_html = "<div>This is content for Validation Test project</div>"
        is_valid, error = ProjectContextAnalyzer.validate_generated_content(
            "<div>Original content</div>", 
            valid_html, 
            context
        )
        assert is_valid
        assert error is None
        
        # Test with content that doesn't include project name
        invalid_html = "<div>This is generic content</div>"
        is_valid, error = ProjectContextAnalyzer.validate_generated_content(
            "<div>Original content</div>", 
            invalid_html, 
            context
        )
        assert not is_valid
        assert error is not None
    
    def test_table_validation(self):
        """Test validation of table content."""
        context = ProjectContext(
            project_name="Table Test",
            project_description="Testing table validation",
            prompt_text="Test tables",
            json_overrides={},
            strict_vars={}
        )
        
        # Original table with sample data
        original_html = """
        <table>
            <tr><th>Phase</th><th>Hours</th><th>Cost</th></tr>
            <tr><td>Design</td><td>100</td><td>$10,000</td></tr>
            <tr><td>Development</td><td>200</td><td>$20,000</td></tr>
            <tr><td>Testing</td><td>50</td><td>$5,000</td></tr>
        </table>
        """
        
        # Generated table with different values
        different_values_html = """
        <table>
            <tr><th>Phase</th><th>Hours</th><th>Cost</th></tr>
            <tr><td>Design</td><td>120</td><td>$12,000</td></tr>
            <tr><td>Development</td><td>250</td><td>$25,000</td></tr>
            <tr><td>Testing</td><td>80</td><td>$8,000</td></tr>
        </table>
        <p>Project: Table Test</p>
        """
        
        # Generated table with copied values
        copied_values_html = """
        <table>
            <tr><th>Phase</th><th>Hours</th><th>Cost</th></tr>
            <tr><td>Design</td><td>100</td><td>$10,000</td></tr>
            <tr><td>Development</td><td>200</td><td>$20,000</td></tr>
            <tr><td>Testing</td><td>50</td><td>$5,000</td></tr>
        </table>
        <p>Project: Table Test</p>
        """
        
        # Test with different values (should be valid)
        is_valid, error = ProjectContextAnalyzer.validate_generated_content(
            original_html, 
            different_values_html, 
            context
        )
        assert is_valid
        assert error is None
        
        # Test with copied values (should be invalid)
        is_valid, error = ProjectContextAnalyzer.validate_generated_content(
            original_html, 
            copied_values_html, 
            context
        )
        assert not is_valid
        assert error is not None