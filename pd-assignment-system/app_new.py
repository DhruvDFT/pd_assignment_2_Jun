import random
import json
import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import os
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
import sqlite3
from threading import Lock
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Database setup
DATABASE = 'assignments.db'
db_lock = Lock()

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

@dataclass
class Submission:
    id: str
    assignment_id: str
    engineer_id: str
    answers: List[str]
    submitted_date: str
    status: str  # 'submitted', 'reviewed', 'graded'
    score: int
    feedback: str
    detailed_scores: List[int]  # Score per question
    detailed_feedback: List[str]  # Feedback per question

class DatabaseManager:
    @staticmethod
    def init_db():
        """Initialize SQLite database"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Create assignments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                title TEXT,
                topic TEXT,
                difficulty INTEGER,
                questions TEXT,
                deliverables TEXT,
                due_date TEXT,
                points INTEGER,
                created_date TEXT,
                engineer_id TEXT
            )
        """)
        
        # Create submissions table
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT,
                engineer_id TEXT,
                answers TEXT,
                submitted_date TEXT,
                status TEXT DEFAULT 'submitted',
                score INTEGER DEFAULT 0,
                feedback TEXT DEFAULT '',
                detailed_scores TEXT DEFAULT '[]',
                detailed_feedback TEXT DEFAULT '[]',
                graded_by TEXT DEFAULT '',
                graded_date TEXT DEFAULT '',
                FOREIGN KEY (assignment_id) REFERENCES assignments (id)
            )
        """)
        
        # Create engineer progress table
        c.execute("""
            CREATE TABLE IF NOT EXISTS engineer_progress (
                engineer_id TEXT PRIMARY KEY,
                completed INTEGER DEFAULT 0,
                current_difficulty INTEGER DEFAULT 1,
                last_assignment_date TEXT,
                total_score INTEGER DEFAULT 0,
                average_score REAL DEFAULT 0.0
            )
        """)
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def save_assignment(assignment: Assignment):
        """Save assignment to database"""
        with db_lock:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO assignments 
                (id, title, topic, difficulty, questions, deliverables, due_date, points, created_date, engineer_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.id, assignment.title, assignment.topic, assignment.difficulty,
                json.dumps(assignment.questions), json.dumps(assignment.deliverables),
                assignment.due_date, assignment.points, assignment.created_date, assignment.engineer_id
            ))
            conn.commit()
            conn.close()
    
    @staticmethod
    def save_submission(submission: Submission):
        """Save submission to database"""
        with db_lock:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO submissions 
                (id, assignment_id, engineer_id, answers, submitted_date, status, score, feedback, detailed_scores, detailed_feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                submission.id, submission.assignment_id, submission.engineer_id,
                json.dumps(submission.answers), submission.submitted_date,
                submission.status, submission.score, submission.feedback,
                json.dumps(submission.detailed_scores), json.dumps(submission.detailed_feedback)
            ))
            conn.commit()
            conn.close()
    
    @staticmethod
    def get_assignment(assignment_id: str, engineer_id: str):
        """Get assignment from database"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM assignments WHERE id = ? AND engineer_id = ?', (assignment_id, engineer_id))
        row = c.fetchone()
        conn.close()
        
        if row:
            return Assignment(
                id=row[0], title=row[1], topic=row[2], difficulty=row[3],
                questions=json.loads(row[4]), deliverables=json.loads(row[5]),
                due_date=row[6], points=row[7], created_date=row[8], engineer_id=row[9]
            )
        return None
    
    @staticmethod
    def get_submission(assignment_id: str, engineer_id: str):
        """Get submission from database"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT * FROM submissions WHERE assignment_id = ? AND engineer_id = ?', (assignment_id, engineer_id))
        row = c.fetchone()
        conn.close()
        
        if row:
            return Submission(
                id=row[0], assignment_id=row[1], engineer_id=row[2],
                answers=json.loads(row[3]), submitted_date=row[4],
                status=row[5], score=row[6], feedback=row[7],
                detailed_scores=json.loads(row[8]) if row[8] else [],
                detailed_feedback=json.loads(row[9]) if row[9] else []
            )
        return None
    
    @staticmethod
    def get_all_assignments():
        """Get all assignments from database"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("""
            SELECT a.*, s.status, s.submitted_date, s.score 
            FROM assignments a 
            LEFT JOIN submissions s ON a.id = s.assignment_id AND a.engineer_id = s.engineer_id
            ORDER BY a.created_date DESC
        """)
        rows = c.fetchall()
        conn.close()
        
        assignments = []
        for row in rows:
            assignment_data = {
                'id': row[0], 'title': row[1], 'topic': row[2], 'difficulty': row[3],
                'questions': json.loads(row[4]), 'deliverables': json.loads(row[5]),
                'due_date': row[6], 'points': row[7], 'created_date': row[8], 'engineer_id': row[9],
                'submission_status': row[10] if row[10] else 'pending',
                'submitted_date': row[11] if row[11] else None,
                'score': row[12] if row[12] else 0
            }
            assignments.append(assignment_data)
        return assignments
    
    @staticmethod
    def get_submissions_for_grading():
        """Get all submitted assignments ready for grading"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("""
            SELECT s.*, a.title, a.topic, a.points, a.questions
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.status = 'submitted'
            ORDER BY s.submitted_date ASC
        """)
        rows = c.fetchall()
        conn.close()
        
        submissions = []
        for row in rows:
            submission_data = {
                'id': row[0], 'assignment_id': row[1], 'engineer_id': row[2],
                'answers': json.loads(row[3]), 'submitted_date': row[4],
                'status': row[5], 'score': row[6], 'feedback': row[7],
                'assignment_title': row[10], 'assignment_topic': row[11],
                'assignment_points': row[12], 'assignment_questions': json.loads(row[13])
            }
            submissions.append(submission_data)
        return submissions

class PDAssignmentGenerator:
    def __init__(self):
        self.topics = {
            "floorplanning": {
                "difficulty_range": (1, 4),
                "question_templates": [
                    "Design a floorplan for a {size} chip with {num_macros} macro blocks. The chip has an aspect ratio of {aspect_ratio} and utilization target of {utilization}%. Discuss your placement strategy.",
                    "Given a design with {power_domains} power domains, explain how you would approach floorplanning to minimize power grid IR drop while maintaining {timing_constraint} timing constraints.",
                    "Compare different floorplanning approaches for a {design_type} design. Justify your choice considering area, timing, and power trade-offs.",
                    "How would you handle floorplanning for a design with {voltage_domains} voltage domains and level shifters?",
                    "Explain the impact of package constraints on your floorplanning decisions for a {package_type} package.",
                    "Design a hierarchical floorplan for a {design_size} design with multiple hierarchy levels.",
                    "How would you optimize floorplan for thermal management in a high-power design?",
                    "Describe your approach to floorplanning for DFT considerations with scan chains.",
                    "How would you handle floorplanning for mixed-signal designs with analog blocks?",
                    "Explain pin assignment strategy for your floorplan considering I/O constraints.",
                    "How would you validate your floorplan meets all timing, power, and area requirements?",
                    "Describe congestion analysis and mitigation strategies in your floorplan.",
                    "How would you handle floorplanning for designs with hard and soft macros?",
                    "Explain your methodology for floorplan optimization iterations and convergence criteria.",
                    "How would you approach floorplanning for low-power designs with power gating?"
                ]
            },
            "placement": {
                "difficulty_range": (2, 5),
                "question_templates": [
                    "Explain the impact of placement on timing for a design running at {frequency} MHz. Discuss congestion vs timing trade-offs.",
                    "Design has {utilization}% utilization and {num_layers} routing layers. Analyze placement strategies to minimize routing congestion.",
                    "Compare global placement vs detailed placement algorithms. When would you choose one over the other for a {design_complexity} design?",
                    "Given timing violations on {violation_type} paths, propose placement-based solutions without changing the netlist.",
                    "How would you handle placement optimization for a design with {clock_domains} clock domains and {skew_budget} ps skew budget?",
                    "Describe placement strategies for power optimization considering {leakage_target}% leakage reduction.",
                    "How would you approach placement for designs with {timing_corners} timing corners and PVT variations?",
                    "Explain placement techniques for minimizing crosstalk in {technology_node} technology.",
                    "How would you handle placement of analog blocks in a mixed-signal design with noise constraints?",
                    "Describe your approach to placement optimization for routability in congested designs.",
                    "How would you handle placement for designs with multiple voltage islands and level shifters?",
                    "Explain placement strategies for clock tree synthesis optimization.",
                    "How would you approach placement for DFT structures and scan chain optimization?",
                    "Describe placement techniques for power grid optimization and IR drop minimization.",
                    "How would you validate placement quality and predict routing success?"
                ]
            },
            "routing": {
                "difficulty_range": (2, 5),
                "question_templates": [
                    "Design has {drc_violations} DRC violations after initial routing. Propose a systematic approach to resolve them.",
                    "Explain routing challenges in {technology_node} technology. How do you handle double patterning constraints?",
                    "Compare different routing algorithms (maze routing, line-search, A*) for a design with {congestion_level} congestion.",
                    "Design requires {layers} metal layers for routing. Justify your layer assignment strategy for different net types.",
                    "How would you handle routing for {differential_pairs} differential pairs with {impedance_target} ohm impedance?",
                    "Describe your approach to power grid routing for {current_density} mA/um current density requirements.",
                    "How would you optimize routing for crosstalk reduction in noisy environments?",
                    "Explain routing strategies for clock networks with {skew_target} ps skew targets.",
                    "How would you handle routing in double patterning technology with coloring constraints?",
                    "Describe routing techniques for high-speed signals with {frequency} GHz switching.",
                    "How would you approach routing for mixed-signal designs with analog isolation requirements?",
                    "Explain routing optimization for manufacturability and yield improvement.",
                    "How would you handle routing congestion resolution without timing degradation?",
                    "Describe routing strategies for power optimization and electromigration prevention.",
                    "How would you validate routing quality and ensure timing closure?"
                ]
            },
            "timing": {
                "difficulty_range": (3, 5),
                "question_templates": [
                    "Setup time violations of {violation_amount} ps on {num_paths} paths. Analyze root causes and propose solutions.",
                    "Clock network has {skew} ps skew across {clock_domains} domains. Design optimization strategy.",
                    "Multi-corner timing analysis shows violations in {corner} corner. Explain your closure methodology.",
                    "Design has {hold_violations} hold violations after CTS. Compare different fixing approaches.",
                    "How would you approach timing optimization in multi-voltage designs with level shifters?",
                    "Describe your methodology for timing correlation between synthesis and P&R tools.",
                    "How would you handle timing closure for high-speed interfaces running at {interface_speed} Gbps?",
                    "Explain timing optimization techniques for low-power designs with voltage scaling.",
                    "How would you approach timing analysis for on-chip variation and process corners?",
                    "Describe timing closure methodology for complex clock domains with generated clocks.",
                    "How would you handle timing optimization for memory interfaces with strict setup/hold requirements?",
                    "Explain timing analysis for asynchronous clock domain crossings and metastability.",
                    "How would you approach timing closure for hierarchical designs with multiple instances?",
                    "Describe timing optimization for process variation tolerance and yield improvement.",
                    "How would you validate timing sign-off across all operating modes and corners?"
                ]
            },
            "power": {
                "difficulty_range": (3, 5),
                "question_templates": [
                    "Power grid analysis shows {ir_drop} mV IR drop. Propose grid strengthening strategies.",
                    "Design has {power_consumption} mW total power. Analyze leakage vs dynamic power optimization techniques.",
                    "Multiple voltage domains with {voltage_levels} different voltages. Design level shifter placement strategy.",
                    "Clock tree consumes {clock_power}% of total power. Propose optimization techniques.",
                    "How would you validate your power optimization results across all operating modes?",
                    "Describe power-aware placement and routing methodology for mobile applications.",
                    "How would you approach power grid design for reliability and electromigration prevention?",
                    "Explain power optimization techniques for always-on domains in IoT designs.",
                    "How would you handle power management for designs with dynamic voltage and frequency scaling?",
                    "Describe power analysis methodology for workloads with varying activity patterns.",
                    "How would you optimize power for AI/ML accelerators with high compute density?",
                    "Explain power integrity analysis and validation for high-performance processors.",
                    "How would you approach power optimization for automotive designs with safety requirements?",
                    "Describe power delivery network design methodology for multi-core processors.",
                    "How would you validate power sign-off across temperature and process variations?"
                ]
            }
        }
    
    def generate_parameters(self, topic: str):
        """Generate random parameters"""
        param_sets = {
            "floorplanning": {
                "size": random.choice(["10mm x 10mm", "15mm x 12mm", "8mm x 16mm"]),
                "num_macros": random.randint(5, 20),
                "aspect_ratio": random.choice(["1:1", "2:1", "1.5:1", "3:2"]),
                "utilization": random.randint(70, 85),
                "power_domains": random.randint(2, 6),
                "timing_constraint": random.choice(["500MHz", "1GHz", "2GHz"]),
                "design_type": random.choice(["CPU", "GPU", "DSP", "mixed-signal"]),
                "voltage_domains": random.randint(2, 4),
                "package_type": random.choice(["BGA", "QFP", "CSP"]),
                "design_size": random.choice(["large", "medium", "complex"])
            },
            "placement": {
                "frequency": random.randint(500, 2000),
                "utilization": random.randint(75, 90),
                "num_layers": random.randint(6, 12),
                "design_complexity": random.choice(["simple", "moderate", "complex"]),
                "violation_type": random.choice(["setup", "hold", "max_transition"]),
                "clock_domains": random.randint(2, 8),
                "skew_budget": random.randint(20, 100),
                "leakage_target": random.randint(10, 30),
                "timing_corners": random.randint(3, 9),
                "technology_node": random.choice(["7nm", "5nm", "3nm"])
            },
            "routing": {
                "drc_violations": random.randint(100, 5000),
                "technology_node": random.choice(["7nm", "5nm", "3nm"]),
                "congestion_level": random.choice(["low", "moderate", "high"]),
                "layers": random.randint(8, 15),
                "differential_pairs": random.randint(10, 50),
                "impedance_target": random.choice([50, 75, 90, 100]),
                "current_density": random.choice([1.5, 2.0, 2.5]),
                "skew_target": random.randint(20, 50),
                "frequency": random.choice([1, 2, 5, 10])
            },
            "timing": {
                "violation_amount": random.randint(10, 200),
                "num_paths": random.randint(20, 500),
                "skew": random.randint(20, 100),
                "clock_domains": random.randint(2, 8),
                "corner": random.choice(["slow", "fast", "typical"]),
                "hold_violations": random.randint(50, 1000),
                "interface_speed": random.choice([1, 2.5, 5, 10, 25])
            },
            "power": {
                "ir_drop": random.randint(50, 200),
                "power_consumption": random.randint(500, 2000),
                "voltage_levels": random.randint(2, 5),
                "clock_power": random.randint(15, 40)
            }
        }
        return param_sets.get(topic, {})
    
    def get_engineer_difficulty(self, engineer_id: str):
        """Get difficulty level"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT current_difficulty FROM engineer_progress WHERE engineer_id = ?', (engineer_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return row[0]
        else:
            with db_lock:
                conn = sqlite3.connect(DATABASE)
                c = conn.cursor()
                c.execute('INSERT INTO engineer_progress VALUES (?, ?, ?, ?, ?, ?)', (engineer_id, 0, 1, None, 0, 0.0))
                conn.commit()
                conn.close()
            return 1
    
    def select_topic_by_difficulty(self, engineer_id: str):
        """Select topic by difficulty"""
        current_diff = self.get_engineer_difficulty(engineer_id)
        suitable_topics = []
        for topic, info in self.topics.items():
            min_diff, max_diff = info["difficulty_range"]
            if min_diff <= current_diff <= max_diff:
                suitable_topics.append(topic)
        return random.choice(suitable_topics) if suitable_topics else "floorplanning"
    
    def generate_assignment(self, engineer_id: str):
        """Generate new assignment with 15 questions"""
        topic = self.select_topic_by_difficulty(engineer_id)
        templates = self.topics[topic]["question_templates"]
        parameters = self.generate_parameters(topic)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        assignment_id = f"PD_{topic.upper()}_{timestamp}"
        
        # Generate 15 questions (all available for the topic)
        all_questions = []
        for template in templates:
            try:
                question = template.format(**parameters)
                all_questions.append(question)
            except KeyError:
                # If template has parameters not in our set, use it as-is
                all_questions.append(template)
        
        # Ensure we have exactly 15 questions
        while len(all_questions) < 15:
            all_questions.append(f"Additional {topic} question: Explain your approach to solving complex {topic} challenges in modern chip design.")
        
        all_questions = all_questions[:15]  # Take first 15
        
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
            difficulty=self.get_engineer_difficulty(engineer_id),
            questions=all_questions,
            deliverables=deliverables,
            due_date=due_date,
            points=100 + (self.get_engineer_difficulty(engineer_id) * 20),
            created_date=datetime.datetime.now().strftime("%Y-%m-%d"),
            engineer_id=engineer_id
        )
        
        return assignment

# Initialize components
generator = PDAssignmentGenerator()

# ========================================
# FIXED FLASK ROUTES - PROPER ROUTING
# ========================================

@app.route('/')
def dashboard():
    """MAIN DASHBOARD - Shows assignments and generation options"""
    assignments = DatabaseManager.get_all_assignments()
    return render_template('dashboard.html', assignments=assignments)

@app.route('/assignment/<assignment_id>/<engineer_id>')
def view_assignment(assignment_id, engineer_id):
    """View specific assignment with questions and submission form"""
    assignment = DatabaseManager.get_assignment(assignment_id, engineer_id)
    submission = DatabaseManager.get_submission(assignment_id, engineer_id)
    
    if assignment:
        difficulty_stars = "★" * assignment.difficulty + "☆" * (5 - assignment.difficulty)
        return render_template('assignment.html', 
                             assignment=assignment, 
                             difficulty_stars=difficulty_stars,
                             submission=submission)
    else:
        return "Assignment not found", 404

@app.route('/grading')
def grading_dashboard():
    """SEPARATE GRADING DASHBOARD - For instructors only"""
    submissions = DatabaseManager.get_submissions_for_grading()
    return render_template('grading_dashboard.html', submissions=submissions)

@app.route('/submit_assignment', methods=['POST'])
def submit_assignment():
    """Handle assignment submission"""
    assignment_id = request.form.get('assignment_id')
    engineer_id = request.form.get('engineer_id')
    
    # Get answers from form
    answers = []
    for i in range(15):  # 15 questions
        answer = request.form.get(f'answer_{i}', '').strip()
        answers.append(answer)
    
    # Validate that at least some answers are provided
    if not any(answer for answer in answers):
        flash('Please provide at least some answers before submitting.', 'error')
        return redirect(url_for('view_assignment', assignment_id=assignment_id, engineer_id=engineer_id))
    
    # Create submission
    submission_id = f"SUB_{assignment_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    submission = Submission(
        id=submission_id,
        assignment_id=assignment_id,
        engineer_id=engineer_id,
        answers=answers,
        submitted_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status='submitted',
        score=0,
        feedback='',
        detailed_scores=[],
        detailed_feedback=[]
    )
    
    DatabaseManager.save_submission(submission)
    
    flash('Assignment submitted successfully! You will receive feedback soon.', 'success')
    return redirect(url_for('view_assignment', assignment_id=assignment_id, engineer_id=engineer_id))

@app.route('/api/generate/<engineer_id>')
def generate_assignment_api(engineer_id):
    """API endpoint to generate new assignment"""
    assignment = generator.generate_assignment(engineer_id)
    DatabaseManager.save_assignment(assignment)
    
    assignment_url = f"/assignment/{assignment.id}/{engineer_id}"
    
    return jsonify({
        'success': True,
        'assignment_id': assignment.id,
        'assignment_url': assignment_url,
        'title': assignment.title,
        'topic': assignment.topic,
        'difficulty': assignment.difficulty,
        'points': assignment.points,
        'due_date': assignment.due_date,
        'question_count': len(assignment.questions)
    })

@app.route('/api/assignments')
def list_assignments_api():
    """API endpoint to list all assignments"""
    assignments = DatabaseManager.get_all_assignments()
    return jsonify(assignments)

@app.route('/api/bulk_generate', methods=['POST'])
def bulk_generate_assignments():
    """Generate assignments for multiple engineers"""
    engineer_ids = request.json.get('engineer_ids', [])
    
    if not engineer_ids:
        return jsonify({'success': False, 'error': 'No engineer IDs provided'})
    
    results = []
    for engineer_id in engineer_ids:
        try:
            assignment = generator.generate_assignment(engineer_id)
            DatabaseManager.save_assignment(assignment)
            results.append({
                'engineer_id': engineer_id,
                'assignment_id': assignment.id,
                'assignment_url': f"/assignment/{assignment.id}/{engineer_id}",
                'success': True
            })
        except Exception as e:
            results.append({
                'engineer_id': engineer_id,
                'success': False,
                'error': str(e)
            })
    
    return jsonify({'success': True, 'results': results})

# Debug routes
@app.route('/debug')
def debug_info():
    """Debug route to check system status"""
    try:
        assignments = DatabaseManager.get_all_assignments()
        test_assignment = generator.generate_assignment("debug_test")
        
        debug_info = {
            "database_connection": "✅ Working",
            "total_assignments": len(assignments),
            "sample_assignment_questions": len(test_assignment.questions) if test_assignment else 0,
            "assignments_list": [
                {
                    "id": a["id"],
                    "engineer_id": a["engineer_id"],
                    "title": a["title"],
                    "questions_count": len(a["questions"]),
                    "url": f"/assignment/{a['id']}/{a['engineer_id']}"
                }
                for a in assignments[:5]
            ]
        }
        
        return f"""
        <h1>🔍 System Debug Information</h1>
        <pre>{json.dumps(debug_info, indent=2)}</pre>
        
        <h2>Quick Actions:</h2>
        <p><a href="/api/generate/debug_test">Generate Test Assignment</a></p>
        <p><a href="/">Go to Main Dashboard</a></p>
        <p><a href="/grading">Go to Grading Dashboard</a></p>
        
        <h2>Recent Assignments:</h2>
        {''.join([f'<p><a href="{a["url"]}">{a["title"]} ({a["engineer_id"]}) - {a["questions_count"]} questions</a></p>' for a in debug_info["assignments_list"]])}
        """
        
    except Exception as e:
        return f"""
        <h1>🚨 System Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/">Try Main Dashboard</a></p>
        """

@app.route('/test_questions')
def test_questions():
    """Show sample questions without database"""
    sample_questions = [
        "Design a floorplan for a 10mm x 10mm chip with 8 macro blocks. Discuss your placement strategy.",
        "Explain the impact of placement on timing for a design running at 1500 MHz.",
        "Design has 2500 DRC violations after initial routing. Propose a systematic approach to resolve them.",
        "Setup time violations of 150 ps on 45 paths. Analyze root causes and propose solutions.",
        "Power grid analysis shows 120 mV IR drop. Propose grid strengthening strategies."
    ]
    
    html = """
    <h1>📋 Sample Assignment Questions</h1>
    <div style="max-width: 800px; margin: 0 auto; font-family: Arial, sans-serif;">
    """
    
    for i, question in enumerate(sample_questions, 1):
        html += f"""
        <div style="background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff;">
            <h3>Question {i}:</h3>
            <p>{question}</p>
            <textarea style="width: 100%; height: 150px; padding: 10px;" placeholder="Your answer here..."></textarea>
        </div>
        """
    
    html += """
    </div>
    <p style="text-align: center;">
        <a href="/">← Back to Dashboard</a>
    </p>
    """
    
    return html

# Initialize database on startup
DatabaseManager.init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
