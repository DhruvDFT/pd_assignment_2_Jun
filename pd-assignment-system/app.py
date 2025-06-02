import random
import json
import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import os
import re
import uuid
from enum import Enum
from flask import Flask, jsonify, request, redirect, session, flash, render_template_string
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Enhanced data structures for submissions
class SubmissionStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    GRADED = "graded"
    RETURNED = "returned"

class AnswerQuality(Enum):
    EXCELLENT = "excellent"  # 300+ words, well-structured
    GOOD = "good"           # 200-299 words, adequate
    FAIR = "fair"           # 150-199 words, basic
    POOR = "poor"           # 50-149 words, insufficient
    MISSING = "missing"     # <50 words or empty

@dataclass
class AnswerAnalysis:
    word_count: int
    character_count: int
    quality: AnswerQuality
    has_technical_terms: bool
    has_examples: bool
    readability_score: float
    estimated_time_spent: int  # minutes
    edit_count: int = 0
    time_spent_seconds: int = 0

@dataclass
class SubmissionMetrics:
    total_words: int
    average_words_per_answer: float
    completion_percentage: float
    quality_distribution: Dict[str, int]
    estimated_total_time: int
    technical_depth_score: float
    overall_quality_score: float

@dataclass
class EnhancedSubmission:
    submission_id: str
    assignment_id: str
    engineer_id: str
    status: SubmissionStatus
    answers: List[str]
    answer_analyses: List[AnswerAnalysis]
    metrics: SubmissionMetrics
    
    # Timestamps
    created_date: str
    last_modified: str
    submitted_date: Optional[str]
    
    # Validation and Quality
    is_complete: bool
    quality_issues: List[str]
    warnings: List[str]
    
    # Submission attempts
    version: int
    auto_saves: List[str]  # timestamps of auto-saves
    
    # Time tracking
    time_spent: Dict[str, int]  # time per question in seconds

# In-memory storage (enhanced)
assignments_store = {}
enhanced_submissions_store = {}  # New enhanced submissions
grades_store = {}
auto_save_store = {}  # Track auto-saves

# Admin credentials (use environment variables in production)
ADMIN_CREDENTIALS = {
    'admin': os.environ.get('ADMIN_PASSWORD', 'pd_admin_2024'),
    'instructor': os.environ.get('INSTRUCTOR_PASSWORD', 'instructor_pass'),
    'supervisor': os.environ.get('SUPERVISOR_PASSWORD', 'super_secure_123')
}

@dataclass
class Assignment:
    id: str
    title: str
    topic: str
    difficulty: int
    questions: List[str]
    deliverables: List[str]
    due_date: str
    points: int
    created_date: str
    engineer_id: str

# Authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/admin_login')
        return f(*args, **kwargs)
    return decorated_function

class SubmissionAnalyzer:
    """Enhanced submission analysis with better algorithms"""
    
    TECHNICAL_TERMS = {
        'floorplanning': ['macro', 'placement', 'routing', 'congestion', 'utilization', 'aspect ratio', 'pin assignment', 'power planning'],
        'placement': ['timing', 'setup', 'hold', 'slack', 'skew', 'fanout', 'load', 'critical path', 'optimization'],
        'routing': ['DRC', 'via', 'metal layer', 'resistance', 'capacitance', 'crosstalk', 'wire delay', 'RC extraction']
    }
    
    @classmethod
    def analyze_answer(cls, answer: str, question_topic: str = None, question_index: int = 0) -> AnswerAnalysis:
        """Comprehensive answer analysis"""
        words = answer.split() if answer.strip() else []
        word_count = len(words)
        char_count = len(answer.strip())
        
        # Determine quality based on word count and structure
        if word_count >= 300:
            quality = AnswerQuality.EXCELLENT
        elif word_count >= 200:
            quality = AnswerQuality.GOOD
        elif word_count >= 150:
            quality = AnswerQuality.FAIR
        elif word_count >= 50:
            quality = AnswerQuality.POOR
        else:
            quality = AnswerQuality.MISSING
        
        # Enhanced technical terms detection
        has_technical_terms = False
        if question_topic and question_topic in cls.TECHNICAL_TERMS:
            terms = cls.TECHNICAL_TERMS[question_topic]
            answer_lower = answer.lower()
            technical_count = sum(1 for term in terms if term in answer_lower)
            has_technical_terms = technical_count >= 2  # At least 2 technical terms
        
        # Enhanced examples detection
        example_phrases = [
            'for example', 'such as', 'like', 'consider', 'suppose',
            'for instance', 'e.g.', 'i.e.', 'namely', 'including',
            'case study', 'scenario', 'implementation'
        ]
        has_examples = any(phrase in answer.lower() for phrase in example_phrases)
        
        # Improved readability score
        sentences = len([s for s in re.split(r'[.!?]+', answer) if s.strip()])
        paragraphs = len([p for p in answer.split('\n\n') if p.strip()])
        
        if sentences > 0:
            avg_sentence_length = word_count / sentences
            readability_score = min(10.0, 10 - abs(avg_sentence_length - 15) * 0.2)  # Optimal ~15 words/sentence
            if paragraphs > 1:
                readability_score += 1  # Bonus for structure
        else:
            readability_score = 0
        
        # Estimate time spent (improved algorithm)
        base_time = word_count // 50  # 50 words per minute typing
        complexity_bonus = 1 if has_technical_terms else 0
        structure_bonus = 1 if paragraphs > 1 else 0
        estimated_time = max(1, base_time + complexity_bonus + structure_bonus)
        
        return AnswerAnalysis(
            word_count=word_count,
            character_count=char_count,
            quality=quality,
            has_technical_terms=has_technical_terms,
            has_examples=has_examples,
            readability_score=readability_score,
            estimated_time_spent=estimated_time
        )
    
    @classmethod
    def calculate_metrics(cls, analyses: List[AnswerAnalysis]) -> SubmissionMetrics:
        """Calculate comprehensive submission metrics"""
        total_words = sum(a.word_count for a in analyses)
        answered_count = sum(1 for a in analyses if a.quality != AnswerQuality.MISSING)
        
        avg_words = total_words / len(analyses) if analyses else 0
        completion_pct = (answered_count / len(analyses)) * 100 if analyses else 0
        
        # Quality distribution
        quality_dist = {}
        for quality in AnswerQuality:
            quality_dist[quality.value] = sum(1 for a in analyses if a.quality == quality)
        
        total_time = sum(a.estimated_time_spent for a in analyses)
        
        # Technical depth score (weighted)
        technical_answers = sum(1 for a in analyses if a.has_technical_terms)
        tech_score = (technical_answers / len(analyses)) * 100 if analyses else 0
        
        # Overall quality score (0-100)
        quality_scores = []
        for analysis in analyses:
            if analysis.quality == AnswerQuality.EXCELLENT:
                score = 95
            elif analysis.quality == AnswerQuality.GOOD:
                score = 85
            elif analysis.quality == AnswerQuality.FAIR:
                score = 75
            elif analysis.quality == AnswerQuality.POOR:
                score = 60
            else:
                score = 0
            
            # Bonuses
            if analysis.has_technical_terms:
                score += 5
            if analysis.has_examples:
                score += 5
            if analysis.readability_score > 7:
                score += 3
            
            quality_scores.append(min(100, score))
        
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return SubmissionMetrics(
            total_words=total_words,
            average_words_per_answer=avg_words,
            completion_percentage=completion_pct,
            quality_distribution=quality_dist,
            estimated_total_time=total_time,
            technical_depth_score=tech_score,
            overall_quality_score=overall_quality
        )
    
    @classmethod
    def validate_submission(cls, answers: List[str], assignment_topic: str = None) -> tuple[bool, List[str], List[str]]:
        """Enhanced submission validation"""
        issues = []
        warnings = []
        
        analyses = [cls.analyze_answer(answer, assignment_topic, i) for i, answer in enumerate(answers)]
        metrics = cls.calculate_metrics(analyses)
        
        # Check completion
        missing_count = sum(1 for a in analyses if a.quality == AnswerQuality.MISSING)
        if missing_count > 0:
            issues.append(f"{missing_count} questions have no meaningful answers (< 50 words)")
        
        # Check quality
        poor_count = sum(1 for a in analyses if a.quality == AnswerQuality.POOR)
        if poor_count > 3:  # Allow some flexibility
            warnings.append(f"{poor_count} answers are below recommended length (< 200 words)")
        
        # Check technical depth
        if metrics.technical_depth_score < 40:
            warnings.append("Consider adding more technical terminology and domain-specific concepts")
        
        # Check overall quality
        if metrics.overall_quality_score < 70:
            issues.append(f"Overall quality score too low ({metrics.overall_quality_score:.1f}/100)")
        
        # Check average length
        if metrics.average_words_per_answer < 180:  # Slightly more flexible
            warnings.append(f"Average answer length ({metrics.average_words_per_answer:.0f} words) could be improved")
        
        is_complete = len(issues) == 0
        
        return is_complete, issues, warnings

class EnhancedSubmissionManager:
    """Enhanced submission management with better features"""
    
    def __init__(self):
        self.submissions = enhanced_submissions_store
        self.auto_saves = auto_save_store
    
    def create_submission(self, assignment_id: str, engineer_id: str) -> EnhancedSubmission:
        """Create new enhanced submission"""
        submission_id = f"enhanced_sub_{assignment_id}_{engineer_id}_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.datetime.now().isoformat()
        
        submission = EnhancedSubmission(
            submission_id=submission_id,
            assignment_id=assignment_id,
            engineer_id=engineer_id,
            status=SubmissionStatus.DRAFT,
            answers=[""] * 15,
            answer_analyses=[],
            metrics=SubmissionMetrics(0, 0, 0, {}, 0, 0, 0),
            created_date=timestamp,
            last_modified=timestamp,
            submitted_date=None,
            is_complete=False,
            quality_issues=[],
            warnings=[],
            version=1,
            auto_saves=[],
            time_spent={str(i): 0 for i in range(15)}
        )
        
        self.submissions[submission_id] = submission
        return submission
    
    def auto_save_submission(self, submission_id: str, answers: List[str], time_spent: Dict[str, int] = None) -> bool:
        """Enhanced auto-save with better tracking"""
        if submission_id not in self.submissions:
            return False
        
        submission = self.submissions[submission_id]
        
        if submission.status != SubmissionStatus.DRAFT:
            return False
        
        # Update answers and metadata
        submission.answers = answers
        submission.last_modified = datetime.datetime.now().isoformat()
        submission.auto_saves.append(submission.last_modified)
        
        if time_spent:
            submission.time_spent.update(time_spent)
        
        # Get assignment topic for better analysis
        assignment_key = f"{submission.assignment_id}_{submission.engineer_id}"
        assignment = assignments_store.get(assignment_key)
        topic = assignment.topic if assignment else None
        
        # Re-analyze answers with topic context
        submission.answer_analyses = [
            SubmissionAnalyzer.analyze_answer(answer, topic, i) 
            for i, answer in enumerate(answers)
        ]
        
        # Update time tracking in analyses
        for i, analysis in enumerate(submission.answer_analyses):
            if str(i) in submission.time_spent:
                analysis.time_spent_seconds = submission.time_spent[str(i)]
        
        submission.metrics = SubmissionAnalyzer.calculate_metrics(submission.answer_analyses)
        
        # Update validation
        is_complete, issues, warnings = SubmissionAnalyzer.validate_submission(answers, topic)
        submission.is_complete = is_complete
        submission.quality_issues = issues
        submission.warnings = warnings
        
        # Store auto-save snapshot
        save_key = f"{submission_id}_{len(submission.auto_saves)}"
        self.auto_saves[save_key] = {
            'timestamp': submission.last_modified,
            'answers': answers.copy(),
            'metrics': asdict(submission.metrics)
        }
        
        return True
    
    def submit_submission(self, submission_id: str, final_answers: List[str]) -> tuple[bool, str]:
        """Enhanced final submission"""
        if submission_id not in self.submissions:
            return False, "Submission not found"
        
        submission = self.submissions[submission_id]
        
        if submission.status != SubmissionStatus.DRAFT:
            return False, f"Cannot submit: submission is already {submission.status.value}"
        
        # Get assignment topic
        assignment_key = f"{submission.assignment_id}_{submission.engineer_id}"
        assignment = assignments_store.get(assignment_key)
        topic = assignment.topic if assignment else None
        
        # Final validation
        is_complete, issues, warnings = SubmissionAnalyzer.validate_submission(final_answers, topic)
        
        if not is_complete:
            return False, f"Submission validation failed: {'; '.join(issues)}"
        
        # Update submission
        submission.answers = final_answers
        submission.status = SubmissionStatus.SUBMITTED
        submission.submitted_date = datetime.datetime.now().isoformat()
        submission.last_modified = submission.submitted_date
        
        # Final analysis
        submission.answer_analyses = [
            SubmissionAnalyzer.analyze_answer(answer, topic, i) 
            for i, answer in enumerate(final_answers)
        ]
        submission.metrics = SubmissionAnalyzer.calculate_metrics(submission.answer_analyses)
        submission.is_complete = True
        submission.quality_issues = []
        submission.version += 1
        
        return True, f"Submission successful! Quality score: {submission.metrics.overall_quality_score:.1f}/100"

# Initialize enhanced submission manager
enhanced_manager = EnhancedSubmissionManager()

class PDAssignmentGenerator:
    def __init__(self):
        self.topics = {
            "floorplanning": [
                "Design a floorplan for a 10mm x 10mm chip with 8 macro blocks. Discuss your placement strategy.",
                "Given a design with 3 power domains, explain how you would approach floorplanning to minimize power grid IR drop.",
                "Compare different floorplanning approaches for a CPU design. Justify your choice considering area, timing, and power trade-offs.",
                "How would you handle floorplanning for a design with 2 voltage domains and level shifters?",
                "Explain the impact of package constraints on your floorplanning decisions for a BGA package.",
                "Design a hierarchical floorplan for a large design with multiple hierarchy levels.",
                "How would you optimize floorplan for thermal management in a high-power design?",
                "Describe your approach to floorplanning for DFT considerations with scan chains.",
                "How would you handle floorplanning for mixed-signal designs with analog blocks?",
                "Explain pin assignment strategy for your floorplan considering I/O constraints.",
                "How would you validate your floorplan meets all timing, power, and area requirements?",
                "Describe congestion analysis and mitigation strategies in your floorplan.",
                "How would you handle floorplanning for designs with hard and soft macros?",
                "Explain your methodology for floorplan optimization iterations and convergence criteria.",
                "How would you approach floorplanning for low-power designs with power gating?"
            ],
            "placement": [
                "Explain the impact of placement on timing for a design running at 1500 MHz. Discuss congestion vs timing trade-offs.",
                "Design has 80% utilization and 10 routing layers. Analyze placement strategies to minimize routing congestion.",
                "Compare global placement vs detailed placement algorithms. When would you choose one over the other?",
                "Given timing violations on setup paths, propose placement-based solutions without changing the netlist.",
                "How would you handle placement optimization for a design with 4 clock domains and 50 ps skew budget?",
                "Describe placement strategies for power optimization considering 20% leakage reduction.",
                "How would you approach placement for designs with 5 timing corners and PVT variations?",
                "Explain placement techniques for minimizing crosstalk in 7nm technology.",
                "How would you handle placement of analog blocks in a mixed-signal design with noise constraints?",
                "Describe your approach to placement optimization for routability in congested designs.",
                "How would you handle placement for designs with multiple voltage islands and level shifters?",
                "Explain placement strategies for clock tree synthesis optimization.",
                "How would you approach placement for DFT structures and scan chain optimization?",
                "Describe placement techniques for power grid optimization and IR drop minimization.",
                "How would you validate placement quality and predict routing success?"
            ],
            "routing": [
                "Design has 2500 DRC violations after initial routing. Propose a systematic approach to resolve them.",
                "Explain routing challenges in 7nm technology. How do you handle double patterning constraints?",
                "Compare different routing algorithms (maze routing, line-search, A*) for a design with high congestion.",
                "Design requires 12 metal layers for routing. Justify your layer assignment strategy for different net types.",
                "How would you handle routing for 25 differential pairs with 100 ohm impedance?",
                "Describe your approach to power grid routing for 2.0 mA/um current density requirements.",
                "How would you optimize routing for crosstalk reduction in noisy environments?",
                "Explain routing strategies for clock networks with 30 ps skew targets.",
                "How would you handle routing in double patterning technology with coloring constraints?",
                "Describe routing techniques for high-speed signals with 5 GHz switching.",
                "How would you approach routing for mixed-signal designs with analog isolation requirements?",
                "Explain routing optimization for manufacturability and yield improvement.",
                "How would you handle routing congestion resolution without timing degradation?",
                "Describe routing strategies for power optimization and electromigration prevention.",
                "How would you validate routing quality and ensure timing closure?"
            ]
        }
    
    def generate_assignment(self, engineer_id: str):
        """Generate new assignment"""
        topic = random.choice(list(self.topics.keys()))
        questions = self.topics[topic]
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        assignment_id = f"PD_{topic.upper()}_{timestamp}"
        
        deliverables = [
            "Detailed written analysis for each question (minimum 200 words per question)",
            "Technical diagrams and sketches where applicable",
            "Trade-off analysis with quantitative justifications",
            "Alternative solutions with pros and cons comparison",
            "References to industry standards and best practices"
        ]
        
        due_date = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        assignment = Assignment(
            id=assignment_id,
            title=f"{topic.title()} Comprehensive Challenge",
            topic=topic,
            difficulty=random.randint(1, 3),
            questions=questions,
            deliverables=deliverables,
            due_date=due_date,
            points=120,
            created_date=datetime.datetime.now().strftime("%Y-%m-%d"),
            engineer_id=engineer_id
        )
        
        # Store assignment
        assignments_store[f"{assignment_id}_{engineer_id}"] = assignment
        
        return assignment

# Initialize generator
generator = PDAssignmentGenerator()

# ========================================
# AUTHENTICATION ROUTES
# ========================================

@app.route('/admin_login')
def admin_login():
    """Admin login page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔐 Admin Login - Physical Design System</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; color: #2c3e50; }
            input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 5px; font-size: 16px; }
            input:focus { border-color: #007bff; outline: none; }
            .btn { background: #007bff; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .header { text-align: center; margin-bottom: 30px; }
            .back-link { text-align: center; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="color: #2c3e50; margin: 0;">🔐 Admin Access</h1>
                <p style="color: #666;">Physical Design Assignment System</p>
            </div>
            
            <form method="POST" action="/admin_login">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required placeholder="Enter admin username">
                </div>
                
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required placeholder="Enter password">
                </div>
                
                <button type="submit" class="btn">🚀 Login as Admin</button>
            </form>
            
            <div class="back-link">
="/admin_login" class="btn">🔐 Admin Login</a>
            </div>
            <p><small>For instructors and administrators only</small></p>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced Physical Design Assignments</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
            .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .btn {{ background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px; border: none; cursor: pointer; }}
            .btn:hover {{ background: #0056b3; }}
            .btn-success {{ background: #28a745; }}
            .btn-success:hover {{ background: #218838; }}
            .btn-info {{ background: #17a2b8; }}
            .btn-info:hover {{ background: #138496; }}
            .btn-warning {{ background: #ffc107; color: #212529; }}
            .btn-warning:hover {{ background: #e0a800; }}
            .btn-danger {{ background: #dc3545; }}
            .btn-danger:hover {{ background: #c82333; }}
            .section {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }}
            h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
            .quick-actions {{ text-align: center; margin: 30px 0; }}
            .status {{ text-align: center; padding: 20px; background: #d4edda; border-radius: 8px; margin: 20px 0; }}
            .enhanced-badge {{ background: linear-gradient(45deg, #007bff, #28a745); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 Enhanced Physical Design Assignment System <span class="enhanced-badge">v2.0</span></h1>
            
            <div class="status">
                <h3>✅ Enhanced System Status: ONLINE</h3>
                <p>🚀 Real-time analysis • 💾 Auto-save • 📊 Advanced metrics • 🎯 Smart validation</p>
            </div>
            
            <div class="section">
                <h2>🎯 Generate Enhanced Assignment</h2>
                <div class="quick-actions">
                    <button class="btn btn-success" onclick="generateEnhancedAssignment()">📝 Generate Enhanced Assignment</button>
                </div>
                <p><strong>✨ New Features:</strong> Real-time quality analysis, auto-save, technical depth scoring</p>
                <p><strong>Topics:</strong> Floorplanning, Placement, Routing (15 questions each)</p>
            </div>

            <div class="section">
                <h2>📊 Enhanced Submissions</h2>
                <div class="quick-actions">
                    <a href="/enhanced_submissions" class="btn btn-info">📋 View Enhanced Submissions</a>
                    <a href="/submission_analytics" class="btn">📈 Analytics Dashboard</a>
                </div>
                <p><strong>Enhanced Features:</strong> Quality scoring, time tracking, auto-save history, validation reports</p>
            </div>
            
            {admin_section}

            <div class="section">
                <h2>🧪 Quick Tests & Legacy</h2>
                <div class="quick-actions">
                    <a href="/api/generate/test_eng_001" class="btn">🚀 Generate Test Assignment</a>
                    <a href="/submissions" class="btn">📋 Legacy Submissions</a>
                    <a href="/health" class="btn">💚 Health Check</a>
                </div>
            </div>

            <div class="section">
                <h2>📊 System Statistics</h2>
                <div id="systemStats">
                    <p>Loading enhanced statistics...</p>
                </div>
            </div>
        </div>

        <script>
        async function generateEnhancedAssignment() {{
            const engineerId = prompt("Enter Engineer ID (e.g., eng_001):");
            if (!engineerId) return;
            
            try {{
                // First generate traditional assignment
                const response = await fetch(`/api/generate/${{engineerId}}`);
                const data = await response.json();
                
                if (data.success) {{
                    // Create enhanced submission
                    const enhancedResponse = await fetch('/api/enhanced-submissions', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            assignment_id: data.assignment_id,
                            engineer_id: engineerId
                        }})
                    }});
                    
                    const enhancedData = await enhancedResponse.json();
                    
                    if (enhancedData.success) {{
                        alert(`✅ Enhanced Assignment Generated Successfully!\\n\\nTitle: ${{data.title}}\\nTopic: ${{data.topic}}\\nQuestions: ${{data.question_count}}\\nSubmission ID: ${{enhancedData.submission_id}}\\n\\nClick OK to view enhanced assignment...`);
                        window.location.href = `/enhanced_assignment/${{data.assignment_id}}/${{engineerId}}/${{enhancedData.submission_id}}`;
                    }} else {{
                        alert('❌ Failed to create enhanced submission: ' + enhancedData.message);
                    }}
                }} else {{
                    alert('❌ Failed to generate assignment: ' + (data.error || 'Unknown error'));
                }}
            }} catch (error) {{
                alert('❌ Error: ' + error.message);
            }}
        }}

        async function loadSystemStats() {{
            try {{
                const [assignmentsResponse, enhancedResponse] = await Promise.all([
                    fetch('/api/assignments'),
                    fetch('/api/enhanced-submissions-stats')
                ]);
                
                const assignments = await assignmentsResponse.json();
                const enhancedStats = enhancedResponse.ok ? await enhancedResponse.json() : {{ total: 0 }};
                
                const statsDiv = document.getElementById('systemStats');
                statsDiv.innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                        <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff;">
                            <h3 style="margin: 0; color: #007bff;">📚 Total Assignments</h3>
                            <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">${{assignments.length}}</p>
                        </div>
                        <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #28a745;">
                            <h3 style="margin: 0; color: #28a745;">🚀 Enhanced Submissions</h3>
                            <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">${{enhancedStats.total || 0}}</p>
                        </div>
                        <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #ffc107;">
                            <h3 style="margin: 0; color: #ffc107;">💾 Auto-saves</h3>
                            <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">${{enhancedStats.auto_saves || 0}}</p>
                        </div>
                        <div style="background: white; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #17a2b8;">
                            <h3 style="margin: 0; color: #17a2b8;">🎯 Avg Quality</h3>
                            <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">${{enhancedStats.avg_quality ? enhancedStats.avg_quality.toFixed(1) : '0.0'}}</p>
                        </div>
                    </div>
                `;
            }} catch (error) {{
                document.getElementById(`technical${{questionIndex}}`).textContent = hasTechnical ? '✅' : '❌';
                
                // Examples check
                const examplePhrases = ['for example', 'such as', 'consider', 'suppose'];
                const hasExamples = examplePhrases.some(phrase => text.toLowerCase().includes(phrase));
                document.getElementById(`examples${{questionIndex}}`).textContent = hasExamples ? '✅' : '❌';
                
                // Estimated time
                const estTime = Math.max(1, Math.ceil(words / 50));
                document.getElementById(`time${{questionIndex}}`).textContent = `${{estTime}}m`;
                
                // Simple quality score
                let qualityScore = 0;
                if (words >= 200) qualityScore += 4;
                else if (words >= 150) qualityScore += 3;
                else if (words >= 100) qualityScore += 2;
                else if (words >= 50) qualityScore += 1;
                
                if (hasTechnical) qualityScore += 2;
                if (hasExamples) qualityScore += 2;
                if (words >= 300) qualityScore += 1;
                
                document.getElementById(`quality${{questionIndex}}`).textContent = qualityScore.toFixed(1);
                
                // Update question status
                const container = textarea.closest('.question-container');
                const statusIndicator = container.querySelector('.status-indicator');
                const statusIcon = container.querySelector('.question-status span:last-child');
                
                if (qualityScore >= 8) {{
                    statusIndicator.className = 'status-indicator status-excellent';
                    statusIndicator.textContent = 'Excellent';
                    statusIcon.textContent = '✅';
                }} else if (qualityScore >= 6) {{
                    statusIndicator.className = 'status-indicator status-good';
                    statusIndicator.textContent = 'Good';
                    statusIcon.textContent = '✅';
                }} else if (qualityScore >= 4) {{
                    statusIndicator.className = 'status-indicator status-fair';
                    statusIndicator.textContent = 'Fair';
                    statusIcon.textContent = '⚠️';
                }} else if (words >= 50) {{
                    statusIndicator.className = 'status-indicator status-poor';
                    statusIndicator.textContent = 'Poor';
                    statusIcon.textContent = '⚠️';
                }} else {{
                    statusIndicator.className = 'status-indicator status-missing';
                    statusIndicator.textContent = 'Missing';
                    statusIcon.textContent = '❌';
                }}
            }}

            function updateOverallMetrics() {{
                const textareas = document.querySelectorAll('.enhanced-textarea');
                let totalWords = 0;
                let answeredQuestions = 0;
                let technicalAnswers = 0;
                let totalQuality = 0;

                textareas.forEach((textarea, index) => {{
                    const text = textarea.value;
                    const words = text.trim() ? text.trim().split(/\\s+/).length : 0;
                    totalWords += words;
                    
                    if (words >= 50) answeredQuestions++;
                    
                    const technicalTerms = ['{hint_text}'.split(', ')];
                    if (technicalTerms.some(term => text.toLowerCase().includes(term))) {{
                        technicalAnswers++;
                    }}
                    
                    // Calculate individual quality
                    let qualityScore = 0;
                    if (words >= 200) qualityScore += 4;
                    else if (words >= 150) qualityScore += 3;
                    else if (words >= 100) qualityScore += 2;
                    else if (words >= 50) qualityScore += 1;
                    
                    totalQuality += qualityScore;
                }});

                const avgWords = answeredQuestions > 0 ? Math.round(totalWords / answeredQuestions) : 0;
                const completion = Math.round((answeredQuestions / textareas.length) * 100);
                const techDepth = Math.round((technicalAnswers / textareas.length) * 100);
                const qualityScore = (totalQuality / textareas.length) * 10; // Scale to 100

                // Update overall metrics display
                document.getElementById('totalWords').textContent = totalWords.toLocaleString();
                document.getElementById('avgWords').textContent = avgWords;
                document.getElementById('completion').textContent = `${{completion}}%`;
                document.getElementById('techDepth').textContent = `${{techDepth}}%`;
                document.getElementById('qualityScore').textContent = qualityScore.toFixed(1);

                // Update submit button state
                const submitButton = document.getElementById('submitBtn');
                const submitStatus = document.getElementById('submitStatus');
                
                if (submitButton && submitStatus) {{
                    if (completion === 100 && avgWords >= 180) {{
                        submitButton.disabled = false;
                        submitButton.style.opacity = '1';
                        submitStatus.textContent = `✅ Ready to submit! Completion: ${{completion}}% | Quality: ${{qualityScore.toFixed(1)}}/100`;
                        submitStatus.style.color = '#155724';
                    }} else {{
                        submitButton.disabled = true;
                        submitButton.style.opacity = '0.6';
                        submitStatus.textContent = `⚠️ Complete remaining questions. Progress: ${{answeredQuestions}}/15 answered`;
                        submitStatus.style.color = '#856404';
                    }}
                }}
            }}

            function updateAllMetrics() {{
                // Update metrics for existing content
                const textareas = document.querySelectorAll('.enhanced-textarea');
                textareas.forEach((textarea, index) => {{
                    if (textarea.value.trim()) {{
                        updateAnswerMetrics(index);
                    }}
                }});
                updateOverallMetrics();
            }}

            function startTimeTracking() {{
                timeTrackingInterval = setInterval(() => {{
                    const sessionTime = Date.now() - sessionStartTime;
                    const questionTime = Date.now() - currentQuestionStartTime;
                    
                    document.getElementById('sessionTime').textContent = formatTime(sessionTime);
                    document.getElementById('questionTime').textContent = formatTime(questionTime);
                }}, 1000);
            }}

            function formatTime(ms) {{
                const minutes = Math.floor(ms / 60000);
                const seconds = Math.floor((ms % 60000) / 1000);
                return `${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
            }}

            function trackQuestionTime(questionIndex) {{
                currentQuestionIndex = questionIndex;
                currentQuestionStartTime = Date.now();
            }}

            function startAutoSave() {{
                // Auto-save every 30 seconds
                autoSaveInterval = setInterval(() => {{
                    autoSave();
                }}, 30000);
            }}

            function autoSave() {{
                const answers = [];
                const textareas = document.querySelectorAll('.enhanced-textarea');
                textareas.forEach(textarea => {{
                    answers.push(textarea.value);
                }});

                // Call enhanced auto-save API
                fetch(`/api/enhanced-submissions/${{submissionId}}/auto-save`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        answers: answers,
                        time_spent: {{}}, // Could track individual question times
                        trigger: 'auto'
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        showAutoSaveIndicator();
                        
                        // Update auto-saves counter
                        document.getElementById('autoSaves').textContent = data.auto_save_count;
                        
                        // Update metrics from server
                        if (data.metrics) {{
                            document.getElementById('totalWords').textContent = data.metrics.total_words.toLocaleString();
                            document.getElementById('avgWords').textContent = data.metrics.average_words_per_answer.toFixed(0);
                            document.getElementById('completion').textContent = `${{data.metrics.completion_percentage.toFixed(0)}}%`;
                            document.getElementById('techDepth').textContent = `${{data.metrics.technical_depth_score.toFixed(0)}}%`;
                            document.getElementById('qualityScore').textContent = data.metrics.overall_quality_score.toFixed(1);
                        }}
                    }}
                }})
                .catch(error => {{
                    console.error('Auto-save failed:', error);
                }});
            }}

            function manualSave() {{
                autoSave();
                alert('💾 Progress saved manually!');
            }}

            function showAutoSaveIndicator() {{
                const indicator = document.getElementById('autoSaveIndicator');
                indicator.classList.add('show');
                setTimeout(() => {{
                    indicator.classList.remove('show');
                }}, 2000);
            }}

            function validateSubmission() {{
                const answers = [];
                const textareas = document.querySelectorAll('.enhanced-textarea');
                textareas.forEach(textarea => {{
                    answers.push(textarea.value);
                }});

                fetch(`/api/enhanced-submissions/${{submissionId}}/validate`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{answers: answers}})
                }})
                .then(response => response.json())
                .then(data => {{
                    const resultsDiv = document.getElementById('validationResults');
                    
                    let html = '';
                    if (data.issues && data.issues.length > 0) {{
                        html += '<div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0;"><h4>❌ Issues (Must Fix):</h4><ul>';
                        data.issues.forEach(issue => {{
                            html += `<li>${{issue}}</li>`;
                        }});
                        html += '</ul></div>';
                    }}
                    
                    if (data.warnings && data.warnings.length > 0) {{
                        html += '<div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0;"><h4>⚠️ Warnings (Recommendations):</h4><ul>';
                        data.warnings.forEach(warning => {{
                            html += `<li>${{warning}}</li>`;
                        }});
                        html += '</ul></div>';
                    }}
                    
                    if (data.is_complete) {{
                        html += '<div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; color: #155724;"><h4>✅ Validation Passed!</h4><p>Your submission meets all quality requirements.</p></div>';
                    }}
                    
                    resultsDiv.innerHTML = html;
                    resultsDiv.style.display = 'block';
                }})
                .catch(error => {{
                    console.error('Validation failed:', error);
                    alert('❌ Validation failed. Please try again.');
                }});
            }}

            function previewSubmission() {{
                const answers = [];
                const textareas = document.querySelectorAll('.enhanced-textarea');
                textareas.forEach(textarea => {{
                    answers.push(textarea.value);
                }});

                const totalWords = answers.reduce((sum, answer) => {{
                    return sum + (answer.trim() ? answer.trim().split(/\\s+/).length : 0);
                }}, 0);

                const answeredCount = answers.filter(answer => answer.trim().split(/\\s+/).length >= 50).length;
                const qualityScore = document.getElementById('qualityScore').textContent;

                alert(`📊 Enhanced Submission Preview\\n\\n` +
                      `✅ Answered Questions: ${{answeredCount}}/15\\n` +
                      `📝 Total Words: ${{totalWords.toLocaleString()}}\\n` +
                      `📈 Average per Answer: ${{Math.round(totalWords / 15)}} words\\n` +
                      `🎯 Quality Score: ${{qualityScore}}/100\\n` +
                      `💾 Auto-saves: ${{document.getElementById('autoSaves').textContent}}\\n\\n` +
                      `${{answeredCount === 15 && totalWords >= 3000 ? '🚀 Ready to submit!' : '⚠️ Complete remaining questions before submitting'}}}`);
            }}

            function submitAssignment() {{
                if (confirm('🚀 Submit Enhanced Assignment?\\n\\nOnce submitted, you cannot make changes. Your submission will be analyzed for quality and completeness. Are you sure?')) {{
                    const answers = [];
                    const textareas = document.querySelectorAll('.enhanced-textarea');
                    textareas.forEach(textarea => {{
                        answers.push(textarea.value);
                    }});

                    const submitButton = document.getElementById('submitBtn');
                    submitButton.disabled = true;
                    submitButton.textContent = '🚀 Submitting...';

                    fetch(`/api/enhanced-submissions/${{submissionId}}/submit`, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{answers: answers}})
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            alert(`✅ Enhanced Assignment Submitted Successfully!\\n\\n${{data.message}}\\n\\nYour submission has been recorded and analyzed.`);
                            window.location.href = '/enhanced_submissions';
                        }} else {{
                            alert(`❌ Submission failed: ${{data.message}}`);
                            submitButton.disabled = false;
                            submitButton.textContent = '🚀 Submit Final';
                        }}
                    }})
                    .catch(error => {{
                        console.error('Submission failed:', error);
                        alert('❌ Submission failed. Please try again.');
                        submitButton.disabled = false;
                        submitButton.textContent = '🚀 Submit Final';
                    }});
                }}
            }}

            // Cleanup intervals when page unloads
            window.addEventListener('beforeunload', function() {{
                if (autoSaveInterval) clearInterval(autoSaveInterval);
                if (timeTrackingInterval) clearInterval(timeTrackingInterval);
                
                // Final auto-save before leaving
                if (!isSubmitted) autoSave();
            }});

            // Keyboard shortcuts
            document.addEventListener('keydown', function(e) {{
                if (!isSubmitted) {{
                    // Ctrl+S for save
                    if (e.ctrlKey && e.key === 's') {{
                        e.preventDefault();
                        manualSave();
                    }}
                    
                    // Ctrl+Enter for validate
                    if (e.ctrlKey && e.key === 'Enter') {{
                        e.preventDefault();
                        validateSubmission();
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

@app.route('/enhanced_submissions')
def enhanced_submissions_view():
    """View all enhanced submissions"""
    if not enhanced_manager.submissions:
        return """
        <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
            <h1>📭 No Enhanced Submissions Yet</h1>
            <p>Generate an enhanced assignment to see submissions here.</p>
            <div style="margin: 20px 0;">
                <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
                <button onclick="generateDemo()" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; margin-left: 10px; cursor: pointer;">🚀 Generate Demo</button>
            </div>
        </div>
        <script>
        function generateDemo() {
            fetch('/api/generate/demo_student')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    fetch('/api/enhanced-submissions', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            assignment_id: data.assignment_id,
                            engineer_id: 'demo_student'
                        })
                    })
                    .then(response => response.json())
                    .then(enhancedData => {
                        if (enhancedData.success) {
                            window.location.href = `/enhanced_assignment/${data.assignment_id}/demo_student/${enhancedData.submission_id}`;
                        }
                    });
                }
            });
        }
        </script>
        """
    
    submissions_html = ""
    for submission_id, submission in enhanced_manager.submissions.items():
        status_color = {
            'draft': '#6c757d',
            'submitted': '#28a745', 
            'under_review': '#ffc107',
            'graded': '#007bff',
            'returned': '#dc3545'
        }.get(submission.status.value, '#6c757d')
        
        submissions_html += f"""
        <div style="background: white; padding: 25px; margin: 20px 0; border-radius: 8px; border-left: 4px solid {status_color}; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <h3 style="margin: 0; color: #2c3e50;">📚 {submission.assignment_id}</h3>
                    <p style="margin: 5px 0;"><strong>👤 Engineer:</strong> {submission.engineer_id}</p>
                    <p style="margin: 5px 0;"><strong>📅 Created:</strong> {submission.created_date}</p>
                    <p style="margin: 5px 0;"><strong>🔄 Last Modified:</strong> {submission.last_modified}</p>
                    {f'<p style="margin: 5px 0;"><strong>📤 Submitted:</strong> {submission.submitted_date}</p>' if submission.submitted_date else ''}
                    <p style="margin: 5px 0;"><strong>📊 Status:</strong> <span style="color: {status_color}; font-weight: bold; text-transform: capitalize;">{submission.status.value}</span></p>
                </div>
                <div style="text-align: right;">
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        <h4 style="margin: 0 0 10px 0; color: #2c3e50;">📊 Quality Metrics</h4>
                        <p style="margin: 2px 0;"><strong>Words:</strong> {submission.metrics.total_words:,}</p>
                        <p style="margin: 2px 0;"><strong>Completion:</strong> {submission.metrics.completion_percentage:.1f}%</p>
                        <p style="margin: 2px 0;"><strong>Quality Score:</strong> {submission.metrics.overall_quality_score:.1f}/100</p>
                        <p style="margin: 2px 0;"><strong>Technical Depth:</strong> {submission.metrics.technical_depth_score:.1f}%</p>
                        <p style="margin: 2px 0;"><strong>Auto-saves:</strong> {len(submission.auto_saves)}</p>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <a href="/enhanced_assignment/{submission.assignment_id}/{submission.engineer_id}/{submission.submission_id}" 
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px;">
                    {'👀 View Submission' if submission.status == SubmissionStatus.SUBMITTED else '📝 Continue Editing'}
                </a>
                <a href="/enhanced_submission_analytics/{submission.submission_id}" 
                   style="background: #17a2b8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-right: 10px;">
                    📈 Analytics
                </a>
                {f'<a href="/grade_enhanced_submission/{submission.submission_id}" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">📝 Grade</a>' if session.get('is_admin') and submission.status == SubmissionStatus.SUBMITTED else ''}
            </div>
            
            {'<div style="background: #d4edda; padding: 10px; border-radius: 5px; margin-top: 15px; color: #155724;"><strong>✅ Complete:</strong> Ready for grading</div>' if submission.is_complete else '<div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 15px; color: #856404;"><strong>⚠️ In Progress:</strong> Continue editing to complete</div>'}
        </div>
        """
    
    # Calculate summary stats
    total_submissions = len(enhanced_manager.submissions)
    completed_submissions = sum(1 for s in enhanced_manager.submissions.values() if s.is_complete)
    avg_quality = sum(s.metrics.overall_quality_score for s in enhanced_manager.submissions.values()) / total_submissions if total_submissions > 0 else 0
    total_auto_saves = sum(len(s.auto_saves) for s in enhanced_manager.submissions.values())
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>📊 Enhanced Submissions Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .enhanced-badge {{ background: linear-gradient(45deg, #007bff, #28a745); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
            .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="text-align: center; color: #2c3e50;">📊 Enhanced Submissions Dashboard <span class="enhanced-badge">v2.0</span></h1>
            
            <div class="stats">
                <div class="stat-card">
                    <h3 style="margin: 0; color: #007bff;">📋 Total Submissions</h3>
                    <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">{total_submissions}</p>
                </div>
                <div class="stat-card">
                    <h3 style="margin: 0; color: #28a745;">✅ Completed</h3>
                    <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">{completed_submissions}</p>
                </div>
                <div class="stat-card">
                    <h3 style="margin: 0; color: #ffc107;">🎯 Avg Quality</h3>
                    <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">{avg_quality:.1f}</p>
                </div>
                <div class="stat-card">
                    <h3 style="margin: 0; color: #17a2b8;">💾 Auto-saves</h3>
                    <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">{total_auto_saves}</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
                <a href="/submission_analytics" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">📈 Analytics</a>
                <a href="/submissions" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">📋 Legacy Submissions</a>
            </div>
            
            <h2 style="color: #2c3e50; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Enhanced Submissions</h2>
            {submissions_html}
        </div>
    </body>
    </html>
    """

# Add API endpoint for enhanced submissions stats
@app.route('/api/enhanced-submissions-stats')
def enhanced_submissions_stats():
    """Get enhanced submissions statistics"""
    total = len(enhanced_manager.submissions)
    completed = sum(1 for s in enhanced_manager.submissions.values() if s.is_complete)
    avg_quality = sum(s.metrics.overall_quality_score for s in enhanced_manager.submissions.values()) / total if total > 0 else 0
    auto_saves = sum(len(s.auto_saves) for s in enhanced_manager.submissions.values())
    
    return jsonify({
        'total': total,
        'completed': completed,
        'avg_quality': avg_quality,
        'auto_saves': auto_saves
    })

# Continue with remaining routes from original app.py...
@app.route('/api/generate/<engineer_id>')
def generate_assignment_api(engineer_id):
    """Generate assignment API"""
    try:
        assignment = generator.generate_assignment(engineer_id)
        
        return jsonify({
            'success': True,
            'assignment_id': assignment.id,
            'assignment_url': f"/assignment/{assignment.id}/{engineer_id}",
            'title': assignment.title,
            'topic': assignment.topic,
            'difficulty': assignment.difficulty,
            'points': assignment.points,
            'due_date': assignment.due_date,
            'question_count': len(assignment.questions)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Enhanced health check"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0-enhanced',
        'assignments_count': len(assignments_store),
        'enhanced_submissions_count': len(enhanced_manager.submissions),
        'total_auto_saves': sum(len(s.auto_saves) for s in enhanced_manager.submissions.values()),
        'admin_logged_in': session.get('is_admin', False),
        'timestamp': datetime.datetime.now().isoformat()
    })

# Legacy routes for backward compatibility
@app.route('/assignment/<assignment_id>/<engineer_id>')
def legacy_assignment_view(assignment_id, engineer_id):
    """Legacy assignment view - redirects to enhanced version"""
    return f"""
    <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
        <h1>🔄 Redirecting to Enhanced Version</h1>
        <p>This assignment is being upgraded to the enhanced submission system...</p>
        <button onclick="createEnhanced()" style="background: #28a745; color: white; padding: 15px 30px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer;">
            🚀 Continue with Enhanced Version
        </button>
        <div style="margin-top: 20px;">
            <a href="/" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
        </div>
    </div>
    <script>
    function createEnhanced() {{
        fetch('/api/enhanced-submissions', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                assignment_id: '{assignment_id}',
                engineer_id: '{engineer_id}'
            }})
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                window.location.href = `/enhanced_assignment/{assignment_id}/{engineer_id}/${{data.submission_id}}`;
            }} else {{
                alert('Error creating enhanced submission: ' + data.message);
            }}
        }});
    }}
    </script>
    """

@app.route('/submissions')
def legacy_submissions():
    """Legacy submissions view"""
    return """
    <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
        <h1>📋 Legacy Submissions</h1>
        <p>This system has been upgraded to Enhanced Submissions v2.0</p>
        <div style="margin: 30px 0;">
            <a href="/enhanced_submissions" style="background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 16px;">
                🚀 View Enhanced Submissions
            </a>
        </div>
        <div>
            <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
        </div>
    </div>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)  # Enable debug for developmentd('systemStats').innerHTML = '<p>❌ Error loading statistics</p>';
            }}
        }}

        // Load stats on page load
        window.addEventListener('DOMContentLoaded', loadSystemStats);
        </script>
    </body>
    </html>
    """

@app.route('/enhanced_assignment/<assignment_id>/<engineer_id>/<submission_id>')
def enhanced_assignment_view(assignment_id, engineer_id, submission_id):
    """Enhanced assignment view with real-time features"""
    assignment_key = f"{assignment_id}_{engineer_id}"
    assignment = assignments_store.get(assignment_key)
    
    if not assignment:
        return f"""
        <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
            <h1>❌ Assignment Not Found</h1>
            <p>Assignment ID: {assignment_id}</p>
            <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
        </div>
        """
    
    submission = enhanced_manager.submissions.get(submission_id)
    if not submission:
        return f"""
        <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
            <h1>❌ Enhanced Submission Not Found</h1>
            <p>Submission ID: {submission_id}</p>
            <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
        </div>
        """
    
    # Check if already submitted
    is_submitted = submission.status == SubmissionStatus.SUBMITTED
    
    # Build questions HTML with enhanced features
    questions_html = ""
    technical_terms_hints = {
        'floorplanning': ['macro', 'placement', 'routing', 'congestion', 'utilization', 'aspect ratio', 'pin assignment'],
        'placement': ['timing', 'setup', 'hold', 'slack', 'skew', 'fanout', 'load', 'critical path'],
        'routing': ['DRC', 'via', 'metal layer', 'resistance', 'capacitance', 'crosstalk', 'wire delay']
    }
    
    hints = technical_terms_hints.get(assignment.topic, [])
    hint_text = ", ".join(hints[:5]) if hints else "technical terminology"
    
    for i, question in enumerate(assignment.questions):
        existing_answer = submission.answers[i] if i < len(submission.answers) else ""
        analysis = submission.answer_analyses[i] if i < len(submission.answer_analyses) else None
        
        # Determine status color and text
        if analysis:
            if analysis.quality == AnswerQuality.EXCELLENT:
                status_class = "status-excellent"
                status_text = "Excellent"
                status_icon = "✅"
            elif analysis.quality == AnswerQuality.GOOD:
                status_class = "status-good"
                status_text = "Good"
                status_icon = "✅"
            elif analysis.quality == AnswerQuality.FAIR:
                status_class = "status-fair"
                status_text = "Fair"
                status_icon = "⚠️"
            elif analysis.quality == AnswerQuality.POOR:
                status_class = "status-poor"
                status_text = "Poor"
                status_icon = "⚠️"
            else:
                status_class = "status-missing"
                status_text = "Missing"
                status_icon = "❌"
        else:
            status_class = "status-missing"
            status_text = "Not started"
            status_icon = "❌"
        
        questions_html += f"""
        <div class="question-container" data-question="{i}">
            <div class="question-header">
                <div class="question-number">Question {i+1}</div>
                <div class="question-status">
                    <span class="status-indicator {status_class}">{status_text}</span>
                    <span style="font-size: 12px;">{status_icon}</span>
                </div>
            </div>
            
            <h4 style="color: #2c3e50; margin: 10px 0;">{question}</h4>
            
            <div class="technical-terms-hint">
                💡 <strong>Technical terms to consider:</strong> {hint_text}
            </div>
            
            <textarea 
                class="enhanced-textarea" 
                data-question-index="{i}"
                placeholder="Enter your detailed answer here (minimum 200 words)..."
                {'disabled' if is_submitted else ''}
            >{existing_answer}</textarea>
            
            <div class="word-counter" id="wordCounter{i}">
                {len(existing_answer.split()) if existing_answer else 0} words
            </div>
            
            <div class="answer-metrics" id="metrics{i}">
                <div class="metric-item">
                    <div class="metric-value" id="words{i}">{analysis.word_count if analysis else 0}</div>
                    <div class="metric-label">Words</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value" id="technical{i}">{'✅' if analysis and analysis.has_technical_terms else '❌'}</div>
                    <div class="metric-label">Technical</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value" id="examples{i}">{'✅' if analysis and analysis.has_examples else '❌'}</div>
                    <div class="metric-label">Examples</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value" id="time{i}">{analysis.estimated_time_spent if analysis else 0}m</div>
                    <div class="metric-label">Est. Time</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value" id="quality{i}">{analysis.readability_score:.1f if analysis else 0.0}</div>
                    <div class="metric-label">Quality</div>
                </div>
            </div>
        </div>
        """
    
    submit_section = ""
    if is_submitted:
        submit_section = f"""
        <div style="background: #d4edda; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <h3 style="color: #155724;">✅ Enhanced Assignment Submitted Successfully!</h3>
            <p>Quality Score: {submission.metrics.overall_quality_score:.1f}/100 | 
               Total Words: {submission.metrics.total_words:,} | 
               Technical Depth: {submission.metrics.technical_depth_score:.1f}%</p>
            <p>Submitted: {submission.submitted_date}</p>
            <p><a href="/enhanced_submissions" style="color: #007bff;">View All Enhanced Submissions →</a></p>
        </div>
        """
    else:
        submit_section = """
        <div class="validation-panel">
            <h3>🔍 Submission Validation</h3>
            <button type="button" class="btn-warning" onclick="validateSubmission()">🔍 Check Quality</button>
            <button type="button" class="btn-warning" onclick="previewSubmission()">👀 Preview Submission</button>
            
            <div id="validationResults" style="margin-top: 15px; display: none;"></div>
        </div>
        
        <div class="submit-section">
            <h3>🚀 Ready to Submit?</h3>
            <p id="submitStatus">Preparing submission status...</p>
            
            <div style="margin: 20px 0;">
                <button type="button" class="btn-primary" onclick="manualSave()" style="margin-right: 10px;">💾 Save Progress</button>
                <button type="button" class="btn-success" onclick="submitAssignment()" id="submitBtn">🚀 Submit Final</button>
            </div>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>📝 Enhanced: {assignment.title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }}
            .enhanced-badge {{ background: linear-gradient(45deg, #007bff, #28a745); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            
            .question-container {{ background: white; margin: 20px 0; padding: 25px; border-radius: 8px; border-left: 4px solid #28a745; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.3s ease; }}
            .question-container:hover {{ box-shadow: 0 4px 15px rgba(0,0,0,0.15); }}
            .question-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .question-number {{ background: #007bff; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; }}
            .question-status {{ display: flex; gap: 10px; align-items: center; }}
            .status-indicator {{ padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
            .status-excellent {{ background: #d4edda; color: #155724; }}
            .status-good {{ background: #cce8f4; color: #0c5460; }}
            .status-fair {{ background: #fff3cd; color: #856404; }}
            .status-poor {{ background: #f8d7da; color: #721c24; }}
            .status-missing {{ background: #f8d7da; color: #721c24; }}
            
            .enhanced-textarea {{ width: 100%; min-height: 150px; padding: 20px; border: 2px solid #ddd; border-radius: 8px; font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; resize: vertical; transition: border-color 0.3s ease; }}
            .enhanced-textarea:focus {{ border-color: #007bff; outline: none; box-shadow: 0 0 0 3px rgba(0,123,255,0.1); }}
            
            .answer-metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 15px; margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; font-size: 13px; }}
            .metric-item {{ text-align: center; }}
            .metric-value {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
            .metric-label {{ color: #6c757d; font-size: 11px; text-transform: uppercase; }}
            
            .technical-terms-hint {{ background: #e7f3ff; border: 1px solid #b3d7ff; border-radius: 5px; padding: 10px; margin: 10px 0; font-size: 12px; color: #0066cc; }}
            .word-counter {{ font-size: 12px; color: #6c757d; text-align: right; margin-top: 5px; }}
            .word-counter.warning {{ color: #ffc107; font-weight: bold; }}
            .word-counter.good {{ color: #28a745; font-weight: bold; }}
            
            .overall-metrics {{ background: #e9ecef; padding: 20px; border-radius: 8px; margin: 30px 0; position: sticky; top: 20px; z-index: 10; }}
            .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
            .metric-card {{ background: white; padding: 15px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
            
            .auto-save-indicator {{ position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 10px 20px; border-radius: 20px; font-size: 14px; opacity: 0; transition: opacity 0.3s ease; z-index: 1000; }}
            .auto-save-indicator.show {{ opacity: 1; }}
            
            .time-tracker {{ position: fixed; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); color: white; padding: 10px 15px; border-radius: 20px; font-size: 12px; z-index: 1000; }}
            
            .validation-panel {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin: 20px 0; }}
            .submit-section {{ background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 25px; text-align: center; margin: 30px 0; }}
            
            .btn-primary {{ background: #007bff; color: white; padding: 15px 30px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }}
            .btn-success {{ background: #28a745; color: white; padding: 15px 30px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }}
            .btn-warning {{ background: #ffc107; color: #212529; padding: 12px 25px; border: none; border-radius: 5px; font-size: 14px; cursor: pointer; margin: 5px; }}
            .btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
        </style>
    </head>
    <body>
        <!-- Auto-save indicator -->
        <div id="autoSaveIndicator" class="auto-save-indicator">✅ Auto-saved</div>

        <!-- Time tracker -->
        <div id="timeTracker" class="time-tracker">
            ⏱️ Session: <span id="sessionTime">00:00</span> | Question: <span id="questionTime">00:00</span>
        </div>

        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1 style="color: #2c3e50; margin: 0;">📝 {assignment.title} <span class="enhanced-badge">Enhanced v2.0</span></h1>
                <p><strong>ID:</strong> {assignment.id} | <strong>Engineer:</strong> {assignment.engineer_id}</p>
                <p><strong>Topic:</strong> {assignment.topic.title()} | <strong>Due:</strong> {assignment.due_date} | <strong>Points:</strong> {assignment.points}</p>
                <p><strong>Submission ID:</strong> {submission_id}</p>
            </div>

            <!-- Overall Metrics Dashboard -->
            <div class="overall-metrics">
                <h3 style="margin: 0 0 15px 0; color: #2c3e50;">📊 Real-time Submission Analysis</h3>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value" id="totalWords">{submission.metrics.total_words}</div>
                        <div class="metric-label">Total Words</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="avgWords">{submission.metrics.average_words_per_answer:.0f}</div>
                        <div class="metric-label">Avg per Answer</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="completion">{submission.metrics.completion_percentage:.0f}%</div>
                        <div class="metric-label">Completion</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="techDepth">{submission.metrics.technical_depth_score:.0f}%</div>
                        <div class="metric-label">Technical Depth</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="qualityScore">{submission.metrics.overall_quality_score:.1f}</div>
                        <div class="metric-label">Quality Score</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="autoSaves">{len(submission.auto_saves)}</div>
                        <div class="metric-label">Auto-saves</div>
                    </div>
                </div>
            </div>

            <!-- Assignment Instructions -->
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <h3>📋 Enhanced Assignment Instructions</h3>
                <ul>
                    <li><strong>Minimum Length:</strong> 200 words per question</li>
                    <li><strong>Auto-save:</strong> Progress automatically saved every 30 seconds</li>
                    <li><strong>Real-time Analysis:</strong> Quality metrics updated as you type</li>
                    <li><strong>Smart Validation:</strong> Pre-submit quality checking with detailed feedback</li>
                    <li><strong>Technical Focus:</strong> Include domain-specific terminology and examples</li>
                </ul>
            </div>

            <!-- Questions Form -->
            <form id="enhancedAssignmentForm">
                <input type="hidden" id="submissionId" value="{submission_id}">
                
                {questions_html}
                
                {submit_section}
            </form>

            <!-- Navigation -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="/" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
                <a href="/enhanced_submissions" style="background: #17a2b8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">📋 Enhanced Submissions</a>
            </div>
        </div>

        <script>
            // Enhanced submission interface JavaScript
            let sessionStartTime = Date.now();
            let currentQuestionStartTime = Date.now();
            let currentQuestionIndex = 0;
            let autoSaveInterval;
            let timeTrackingInterval;
            let submissionId = document.getElementById('submissionId').value;
            let isSubmitted = {str(is_submitted).lower()};

            // Initialize enhanced interface
            document.addEventListener('DOMContentLoaded', function() {{
                if (!isSubmitted) {{
                    initializeInterface();
                    startTimeTracking();
                    startAutoSave();
                }}
                updateAllMetrics();
            }});

            function initializeInterface() {{
                const textareas = document.querySelectorAll('.enhanced-textarea');
                textareas.forEach((textarea, index) => {{
                    textarea.addEventListener('input', function() {{
                        updateAnswerMetrics(index);
                        updateOverallMetrics();
                        trackQuestionTime(index);
                    }});
                    
                    textarea.addEventListener('focus', function() {{
                        currentQuestionIndex = index;
                        currentQuestionStartTime = Date.now();
                    }});
                }});
            }}

            function updateAnswerMetrics(questionIndex) {{
                const textarea = document.querySelector(`[data-question-index="${{questionIndex}}"]`);
                const text = textarea.value;
                const words = text.trim() ? text.trim().split(/\\s+/).length : 0;
                
                // Update word counter
                const wordCounter = document.getElementById(`wordCounter${{questionIndex}}`);
                if (words >= 300) {{
                    wordCounter.className = 'word-counter good';
                    wordCounter.textContent = `${{words}} words ✅ Excellent quality`;
                }} else if (words >= 200) {{
                    wordCounter.className = 'word-counter good';
                    wordCounter.textContent = `${{words}} words ✅ Good quality`;
                }} else if (words >= 150) {{
                    wordCounter.className = 'word-counter warning';
                    wordCounter.textContent = `${{words}} words ⚠️ Fair quality`;
                }} else if (words >= 50) {{
                    wordCounter.className = 'word-counter warning';
                    wordCounter.textContent = `${{words}} words ⚠️ Below recommended`;
                }} else {{
                    wordCounter.className = 'word-counter';
                    wordCounter.textContent = `${{words}} words - Continue writing...`;
                }}

                // Update individual metrics
                document.getElementById(`words${{questionIndex}}`).textContent = words;
                
                // Simple technical terms check
                const technicalTerms = ['{hint_text}'.split(', ')];
                const hasTechnical = technicalTerms.some(term => text.toLowerCase().includes(term));
                document.getElementByI="/" style="color: #007bff; text-decoration: none;">← Back to Main Dashboard</a>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background: #e9ecef; border-radius: 5px; font-size: 14px;">
                <strong>Demo Credentials:</strong><br>
                Username: <code>admin</code><br>
                Password: <code>pd_admin_2024</code>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/admin_login', methods=['POST'])
def handle_admin_login():
    """Handle admin login"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
        session['is_admin'] = True
        session['admin_username'] = username
        return redirect('/admin_dashboard')
    else:
        return """
        <script>
            alert('❌ Invalid credentials! Please try again.');
            window.location.href = '/admin_login';
        </script>
        """

@app.route('/admin_logout')
def admin_logout():
    """Admin logout"""
    session.pop('is_admin', None)
    session.pop('admin_username', None)
    return """
    <script>
        alert('✅ Logged out successfully!');
        window.location.href = '/';
    </script>
    """

# ========================================
# ENHANCED API ROUTES
# ========================================

@app.route('/api/enhanced-submissions', methods=['POST'])
def create_enhanced_submission():
    """Create new enhanced submission"""
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    engineer_id = data.get('engineer_id')
    
    if not assignment_id or not engineer_id:
        return jsonify({'error': 'Missing assignment_id or engineer_id'}), 400
    
    submission = enhanced_manager.create_submission(assignment_id, engineer_id)
    
    return jsonify({
        'success': True,
        'submission_id': submission.submission_id,
        'message': 'Enhanced submission created successfully'
    })

@app.route('/api/enhanced-submissions/<submission_id>/auto-save', methods=['POST'])
def auto_save_enhanced_submission(submission_id):
    """Auto-save enhanced submission"""
    data = request.get_json()
    answers = data.get('answers', [])
    time_spent = data.get('time_spent', {})
    
    success = enhanced_manager.auto_save_submission(submission_id, answers, time_spent)
    
    if success:
        submission = enhanced_manager.submissions[submission_id]
        return jsonify({
            'success': True,
            'message': 'Auto-saved successfully',
            'metrics': asdict(submission.metrics),
            'auto_save_count': len(submission.auto_saves),
            'is_complete': submission.is_complete,
            'quality_issues': submission.quality_issues,
            'warnings': submission.warnings
        })
    else:
        return jsonify({'success': False, 'message': 'Auto-save failed'}), 400

@app.route('/api/enhanced-submissions/<submission_id>/validate', methods=['POST'])
def validate_enhanced_submission(submission_id):
    """Validate enhanced submission"""
    data = request.get_json()
    answers = data.get('answers', [])
    
    # Get assignment topic
    submission = enhanced_manager.submissions.get(submission_id)
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404
    
    assignment_key = f"{submission.assignment_id}_{submission.engineer_id}"
    assignment = assignments_store.get(assignment_key)
    topic = assignment.topic if assignment else None
    
    is_complete, issues, warnings = SubmissionAnalyzer.validate_submission(answers, topic)
    
    analyses = [SubmissionAnalyzer.analyze_answer(answer, topic, i) for i, answer in enumerate(answers)]
    metrics = SubmissionAnalyzer.calculate_metrics(analyses)
    
    return jsonify({
        'is_complete': is_complete,
        'issues': issues,
        'warnings': warnings,
        'metrics': asdict(metrics),
        'answer_analyses': [asdict(analysis) for analysis in analyses]
    })

@app.route('/api/enhanced-submissions/<submission_id>/submit', methods=['POST'])
def submit_enhanced_submission(submission_id):
    """Submit final enhanced submission"""
    data = request.get_json()
    answers = data.get('answers', [])
    
    success, message = enhanced_manager.submit_submission(submission_id, answers)
    
    if success:
        submission = enhanced_manager.submissions[submission_id]
        return jsonify({
            'success': True,
            'message': message,
            'final_metrics': asdict(submission.metrics),
            'submitted_at': submission.submitted_date
        })
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/api/enhanced-submissions/<submission_id>', methods=['GET'])
def get_enhanced_submission(submission_id):
    """Get enhanced submission details"""
    submission = enhanced_manager.submissions.get(submission_id)
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404
    
    return jsonify({
        'submission_id': submission.submission_id,
        'assignment_id': submission.assignment_id,
        'engineer_id': submission.engineer_id,
        'status': submission.status.value,
        'answers': submission.answers,
        'metrics': asdict(submission.metrics),
        'answer_analyses': [asdict(analysis) for analysis in submission.answer_analyses],
        'is_complete': submission.is_complete,
        'quality_issues': submission.quality_issues,
        'warnings': submission.warnings,
        'created_date': submission.created_date,
        'last_modified': submission.last_modified,
        'submitted_date': submission.submitted_date,
        'version': submission.version,
        'auto_save_count': len(submission.auto_saves)
    })

# ========================================
# ENHANCED ROUTES (PUBLIC & ADMIN)
# ========================================

@app.route('/')
def index():
    """Enhanced main dashboard"""
    admin_section = ""
    if session.get('is_admin'):
        admin_section = """
        <div class="section">
            <h2>🎓 Admin Panel</h2>
            <div class="quick-actions">
                <a href="/admin_dashboard" class="btn btn-warning">🎓 Admin Dashboard</a>
                <a href="/enhanced_submissions_admin" class="btn btn-info">📊 Enhanced Submissions</a>
                <a href="/admin_logout" class="btn btn-danger">🚪 Logout</a>
            </div>
        </div>
        """
    else:
        admin_section = """
        <div class="section">
            <h2>🔐 Admin Access</h2>
            <div class="quick-actions">
                <a href
