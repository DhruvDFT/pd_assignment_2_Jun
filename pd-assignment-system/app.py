# ===========================================
# FILE 1: requirements.txt
# ===========================================
Flask==2.3.3
gunicorn==21.2.0

# ===========================================
# FILE 2: Procfile (for Railway)
# ===========================================
web: gunicorn app:app --bind 0.0.0.0:$PORT

# ===========================================
# FILE 3: railway.toml (Railway configuration)
# ===========================================
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn app:app --bind 0.0.0.0:$PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

# ===========================================
# FILE 4: Updated app.py (WSGI compatible)
# ===========================================

import random
import json
import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import os
import re
import uuid
from enum import Enum
from flask import Flask, jsonify, request, redirect, session, render_template_string
from functools import wraps

# Initialize Flask app with WSGI compatibility
app = Flask(__name__)

# Railway-compatible configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'railway-secret-key-change-in-production')

# Enhanced data structures for submissions
class SubmissionStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    GRADED = "graded"
    RETURNED = "returned"

class AnswerQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    MISSING = "missing"

@dataclass
class AnswerAnalysis:
    word_count: int
    character_count: int
    quality: AnswerQuality
    has_technical_terms: bool
    has_examples: bool
    readability_score: float
    estimated_time_spent: int
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
    created_date: str
    last_modified: str
    submitted_date: Optional[str]
    is_complete: bool
    quality_issues: List[str]
    warnings: List[str]
    version: int
    auto_saves: List[str]
    time_spent: Dict[str, int]

# In-memory storage (Railway compatible)
assignments_store = {}
enhanced_submissions_store = {}
grades_store = {}

# Admin credentials
ADMIN_CREDENTIALS = {
    'admin': os.environ.get('ADMIN_PASSWORD', 'pd_admin_2024'),
    'instructor': os.environ.get('INSTRUCTOR_PASSWORD', 'instructor_pass')
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
    """Enhanced submission analysis"""
    
    TECHNICAL_TERMS = {
        'floorplanning': ['macro', 'placement', 'routing', 'congestion', 'utilization', 'aspect ratio'],
        'placement': ['timing', 'setup', 'hold', 'slack', 'skew', 'fanout', 'load'],
        'routing': ['DRC', 'via', 'metal layer', 'resistance', 'capacitance', 'crosstalk']
    }
    
    @classmethod
    def analyze_answer(cls, answer: str, question_topic: str = None, question_index: int = 0) -> AnswerAnalysis:
        try:
            words = answer.split() if answer.strip() else []
            word_count = len(words)
            char_count = len(answer.strip())
            
            # Quality assessment
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
            
            # Technical terms detection
            has_technical_terms = False
            if question_topic and question_topic in cls.TECHNICAL_TERMS:
                terms = cls.TECHNICAL_TERMS[question_topic]
                answer_lower = answer.lower()
                technical_count = sum(1 for term in terms if term in answer_lower)
                has_technical_terms = technical_count >= 1
            
            # Examples detection
            example_phrases = ['for example', 'such as', 'like', 'consider', 'suppose', 'e.g.']
            has_examples = any(phrase in answer.lower() for phrase in example_phrases)
            
            # Readability score
            sentences = len([s for s in re.split(r'[.!?]+', answer) if s.strip()])
            if sentences > 0:
                avg_sentence_length = word_count / sentences
                readability_score = min(10.0, 10 - abs(avg_sentence_length - 15) * 0.2)
            else:
                readability_score = 0
            
            # Time estimation
            estimated_time = max(1, word_count // 50)
            
            return AnswerAnalysis(
                word_count=word_count,
                character_count=char_count,
                quality=quality,
                has_technical_terms=has_technical_terms,
                has_examples=has_examples,
                readability_score=readability_score,
                estimated_time_spent=estimated_time
            )
        except Exception as e:
            # Fallback for any analysis errors
            return AnswerAnalysis(0, 0, AnswerQuality.MISSING, False, False, 0.0, 0)
    
    @classmethod
    def calculate_metrics(cls, analyses: List[AnswerAnalysis]) -> SubmissionMetrics:
        try:
            total_words = sum(a.word_count for a in analyses)
            answered_count = sum(1 for a in analyses if a.quality != AnswerQuality.MISSING)
            
            avg_words = total_words / len(analyses) if analyses else 0
            completion_pct = (answered_count / len(analyses)) * 100 if analyses else 0
            
            # Quality distribution
            quality_dist = {}
            for quality in AnswerQuality:
                quality_dist[quality.value] = sum(1 for a in analyses if a.quality == quality)
            
            total_time = sum(a.estimated_time_spent for a in analyses)
            
            # Technical depth score
            technical_answers = sum(1 for a in analyses if a.has_technical_terms)
            tech_score = (technical_answers / len(analyses)) * 100 if analyses else 0
            
            # Overall quality score
            quality_scores = []
            for analysis in analyses:
                if analysis.quality == AnswerQuality.EXCELLENT:
                    score = 90
                elif analysis.quality == AnswerQuality.GOOD:
                    score = 80
                elif analysis.quality == AnswerQuality.FAIR:
                    score = 70
                elif analysis.quality == AnswerQuality.POOR:
                    score = 50
                else:
                    score = 0
                
                if analysis.has_technical_terms:
                    score += 5
                if analysis.has_examples:
                    score += 5
                
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
        except Exception as e:
            # Fallback metrics
            return SubmissionMetrics(0, 0, 0, {}, 0, 0, 0)

class EnhancedSubmissionManager:
    """Enhanced submission management"""
    
    def __init__(self):
        self.submissions = enhanced_submissions_store
    
    def create_submission(self, assignment_id: str, engineer_id: str) -> EnhancedSubmission:
        try:
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
        except Exception as e:
            raise Exception(f"Failed to create submission: {str(e)}")
    
    def auto_save_submission(self, submission_id: str, answers: List[str], time_spent: Dict[str, int] = None) -> bool:
        try:
            if submission_id not in self.submissions:
                return False
            
            submission = self.submissions[submission_id]
            
            if submission.status != SubmissionStatus.DRAFT:
                return False
            
            # Update submission
            submission.answers = answers
            submission.last_modified = datetime.datetime.now().isoformat()
            submission.auto_saves.append(submission.last_modified)
            
            if time_spent:
                submission.time_spent.update(time_spent)
            
            # Get assignment topic
            assignment_key = f"{submission.assignment_id}_{submission.engineer_id}"
            assignment = assignments_store.get(assignment_key)
            topic = assignment.topic if assignment else None
            
            # Re-analyze answers
            submission.answer_analyses = [
                SubmissionAnalyzer.analyze_answer(answer, topic, i) 
                for i, answer in enumerate(answers)
            ]
            
            submission.metrics = SubmissionAnalyzer.calculate_metrics(submission.answer_analyses)
            
            return True
        except Exception as e:
            print(f"Auto-save error: {str(e)}")
            return False
    
    def submit_submission(self, submission_id: str, final_answers: List[str]) -> tuple[bool, str]:
        try:
            if submission_id not in self.submissions:
                return False, "Submission not found"
            
            submission = self.submissions[submission_id]
            
            if submission.status != SubmissionStatus.DRAFT:
                return False, f"Cannot submit: submission is already {submission.status.value}"
            
            # Get assignment topic
            assignment_key = f"{submission.assignment_id}_{submission.engineer_id}"
            assignment = assignments_store.get(assignment_key)
            topic = assignment.topic if assignment else None
            
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
        except Exception as e:
            return False, f"Submission error: {str(e)}"

# Initialize managers
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
        try:
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
            
            assignments_store[f"{assignment_id}_{engineer_id}"] = assignment
            return assignment
        except Exception as e:
            raise Exception(f"Failed to generate assignment: {str(e)}")

generator = PDAssignmentGenerator()

# ========================================
# BASIC ROUTES
# ========================================

@app.route('/')
def index():
    """Railway-optimized main dashboard"""
    try:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Enhanced Physical Design Assignments - Railway</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .btn { background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px; border: none; cursor: pointer; }
                .btn:hover { background: #0056b3; }
                .btn-success { background: #28a745; }
                .section { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }
                h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
                .status { text-align: center; padding: 20px; background: #d4edda; border-radius: 8px; margin: 20px 0; }
                .enhanced-badge { background: linear-gradient(45deg, #007bff, #28a745); color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📚 Enhanced Physical Design System <span class="enhanced-badge">Railway v2.0</span></h1>
                
                <div class="status">
                    <h3>✅ Railway Deployment: ONLINE</h3>
                    <p>🚀 Real-time analysis • 💾 Auto-save • 📊 Advanced metrics</p>
                </div>
                
                <div class="section">
                    <h2>🎯 Generate Enhanced Assignment</h2>
                    <div style="text-align: center;">
                        <button class="btn btn-success" onclick="generateEnhancedAssignment()">📝 Generate Enhanced Assignment</button>
                    </div>
                    <p><strong>Features:</strong> Real-time quality analysis, auto-save, technical depth scoring</p>
                </div>

                <div class="section">
                    <h2>📊 Enhanced Submissions</h2>
                    <div style="text-align: center;">
                        <a href="/enhanced_submissions" class="btn">📋 View Enhanced Submissions</a>
                        <a href="/health" class="btn">💚 Health Check</a>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🔐 Admin Access</h2>
                    <div style="text-align: center;">
                        <a href="/admin_login" class="btn">🔐 Admin Login</a>
                    </div>
                </div>
            </div>

            <script>
            async function generateEnhancedAssignment() {
                const engineerId = prompt("Enter Engineer ID (e.g., eng_001):");
                if (!engineerId) return;
                
                try {
                    const response = await fetch(`/api/generate/${engineerId}`);
                    const data = await response.json();
                    
                    if (data.success) {
                        const enhancedResponse = await fetch('/api/enhanced-submissions', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                assignment_id: data.assignment_id,
                                engineer_id: engineerId
                            })
                        });
                        
                        const enhancedData = await enhancedResponse.json();
                        
                        if (enhancedData.success) {
                            alert(`✅ Enhanced Assignment Generated!\\n\\nTitle: ${data.title}\\nTopic: ${data.topic}`);
                            window.location.href = `/enhanced_assignment/${data.assignment_id}/${engineerId}/${enhancedData.submission_id}`;
                        } else {
                            alert('❌ Failed to create enhanced submission');
                        }
                    } else {
                        alert('❌ Failed to generate assignment');
                    }
                } catch (error) {
                    alert('❌ Error: ' + error.message);
                }
            }
            </script>
        </body>
        </html>
        '''
    except Exception as e:
        return f"<h1>Error loading dashboard: {str(e)}</h1>"

# ========================================
# API ROUTES
# ========================================

@app.route('/api/enhanced-submissions', methods=['POST'])
def create_enhanced_submission():
    """Create new enhanced submission"""
    try:
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate/<engineer_id>')
def generate_assignment_api(engineer_id):
    """Generate assignment API"""
    try:
        assignment = generator.generate_assignment(engineer_id)
        
        return jsonify({
            'success': True,
            'assignment_id': assignment.id,
            'title': assignment.title,
            'topic': assignment.topic,
            'difficulty': assignment.difficulty,
            'points': assignment.points,
            'due_date': assignment.due_date,
            'question_count': len(assignment.questions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Railway health check"""
    try:
        return jsonify({
            'status': 'healthy',
            'version': '2.0-railway',
            'platform': 'Railway',
            'gunicorn': 'compatible',
            'assignments_count': len(assignments_store),
            'enhanced_submissions_count': len(enhanced_manager.submissions),
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ========================================
# WSGI APPLICATION FOR RAILWAY/GUNICORN
# ========================================

# This is what Gunicorn will look for
application = app

if __name__ == '__main__':
    # For local development only
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
