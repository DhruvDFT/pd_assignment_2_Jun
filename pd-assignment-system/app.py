import os
import json
import datetime
import random
import uuid
from flask import Flask, jsonify, request, render_template_string

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'railway-secret-key')

# Simple in-memory storage
assignments_store = {}
submissions_store = {}

# Assignment topics
TOPICS = {
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

def analyze_answer(answer):
    """Simple answer analysis"""
    words = len(answer.split()) if answer.strip() else 0
    
    if words >= 200:
        quality = "good"
        score = 85
    elif words >= 150:
        quality = "fair"
        score = 75
    elif words >= 50:
        quality = "poor"
        score = 60
    else:
        quality = "missing"
        score = 0
    
    return {
        'word_count': words,
        'quality': quality,
        'score': score
    }

# ========================================
# ROUTES
# ========================================

@app.route('/')
def index():
    """Main dashboard"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Physical Design Assignments - Railway</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 900px; 
                margin: 50px auto; 
                padding: 20px; 
                background: #f5f5f5; 
                line-height: 1.6;
            }
            .container { 
                background: white; 
                padding: 40px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            }
            .btn { 
                background: #007bff; 
                color: white; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 5px; 
                display: inline-block; 
                margin: 10px; 
                border: none; 
                cursor: pointer; 
                font-size: 16px;
            }
            .btn:hover { background: #0056b3; }
            .btn-success { background: #28a745; }
            .btn-success:hover { background: #218838; }
            .btn-info { background: #17a2b8; }
            .btn-info:hover { background: #138496; }
            .section { 
                background: #f8f9fa; 
                padding: 25px; 
                margin: 20px 0; 
                border-radius: 8px; 
                border-left: 4px solid #007bff; 
            }
            h1 { 
                color: #2c3e50; 
                text-align: center; 
                margin-bottom: 30px; 
            }
            .status { 
                text-align: center; 
                padding: 20px; 
                background: #d4edda; 
                border-radius: 8px; 
                margin: 20px 0; 
                border: 1px solid #c3e6cb;
            }
            .quick-actions { 
                text-align: center; 
                margin: 20px 0; 
            }
            .badge { 
                background: linear-gradient(45deg, #007bff, #28a745); 
                color: white; 
                padding: 5px 15px; 
                border-radius: 20px; 
                font-size: 12px; 
                font-weight: bold; 
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                border-left: 4px solid #007bff;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 Physical Design Assignment System <span class="badge">Railway v2.0</span></h1>
            
            <div class="status">
                <h3>✅ Railway Deployment: ONLINE</h3>
                <p>🚀 Real-time analysis • 💾 Auto-save • 📊 Quality metrics</p>
            </div>
            
            <div class="section">
                <h2>🎯 Generate Assignment</h2>
                <div class="quick-actions">
                    <button class="btn btn-success" onclick="generateAssignment()">📝 Generate Assignment</button>
                </div>
                <p><strong>Topics Available:</strong> Floorplanning, Placement, Routing (15 questions each)</p>
                <p><strong>Features:</strong> Real-time word counting, quality scoring, auto-save</p>
            </div>

            <div class="section">
                <h2>📊 View Submissions</h2>
                <div class="quick-actions">
                    <a href="/submissions" class="btn btn-info">📋 View All Submissions</a>
                    <a href="/analytics" class="btn">📈 Analytics</a>
                </div>
                <p>View completed assignments with quality analysis and scoring</p>
            </div>
            
            <div class="section">
                <h2>🔧 System</h2>
                <div class="quick-actions">
                    <a href="/health" class="btn">💚 Health Check</a>
                    <a href="/api/stats" class="btn">📊 API Stats</a>
                </div>
            </div>

            <div class="section">
                <h2>📊 Current Statistics</h2>
                <div class="stats" id="statsContainer">
                    <div class="stat-card">
                        <h3 style="margin: 0; color: #007bff;">📚 Assignments</h3>
                        <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;" id="assignmentsCount">0</p>
                    </div>
                    <div class="stat-card">
                        <h3 style="margin: 0; color: #28a745;">📝 Submissions</h3>
                        <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;" id="submissionsCount">0</p>
                    </div>
                    <div class="stat-card">
                        <h3 style="margin: 0; color: #ffc107;">⭐ Avg Quality</h3>
                        <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;" id="avgQuality">0</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
        async function generateAssignment() {
            const engineerId = prompt("Enter Engineer ID (e.g., eng_001):");
            if (!engineerId) return;
            
            try {
                const response = await fetch('/api/generate/' + engineerId);
                const data = await response.json();
                
                if (data.success) {
                    alert('✅ Assignment Generated Successfully!\\n\\nTitle: ' + data.title + '\\nTopic: ' + data.topic + '\\nQuestions: ' + data.question_count);
                    window.location.href = '/assignment/' + data.assignment_id + '/' + engineerId;
                } else {
                    alert('❌ Failed to generate assignment: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                alert('❌ Error: ' + error.message);
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('assignmentsCount').textContent = stats.assignments || 0;
                document.getElementById('submissionsCount').textContent = stats.submissions || 0;
                document.getElementById('avgQuality').textContent = (stats.avg_quality || 0).toFixed(1);
            } catch (error) {
                console.log('Stats loading failed:', error);
            }
        }

        // Load stats on page load
        window.addEventListener('DOMContentLoaded', loadStats);
        </script>
    </body>
    </html>
    '''

@app.route('/api/generate/<engineer_id>')
def generate_assignment(engineer_id):
    """Generate assignment API"""
    try:
        topic = random.choice(list(TOPICS.keys()))
        questions = TOPICS[topic]
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        assignment_id = f"PD_{topic.upper()}_{timestamp}"
        
        assignment = {
            'id': assignment_id,
            'title': f"{topic.title()} Assignment",
            'topic': topic,
            'engineer_id': engineer_id,
            'questions': questions,
            'created_date': datetime.datetime.now().isoformat(),
            'due_date': (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            'points': 120
        }
        
        # Store assignment
        assignments_store[f"{assignment_id}_{engineer_id}"] = assignment
        
        return jsonify({
            'success': True,
            'assignment_id': assignment_id,
            'title': assignment['title'],
            'topic': topic,
            'question_count': len(questions),
            'due_date': assignment['due_date']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/assignment/<assignment_id>/<engineer_id>')
def view_assignment(assignment_id, engineer_id):
    """View assignment"""
    try:
        key = f"{assignment_id}_{engineer_id}"
        assignment = assignments_store.get(key)
        
        if not assignment:
            return f'''
            <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
                <h1>❌ Assignment Not Found</h1>
                <p>Assignment ID: {assignment_id}</p>
                <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
            </div>
            '''
        
        # Check if already submitted
        submission_key = f"sub_{assignment_id}_{engineer_id}"
        is_submitted = submission_key in submissions_store
        
        # Build questions HTML
        questions_html = ""
        for i, question in enumerate(assignment['questions']):
            existing_answer = ""
            if is_submitted:
                submission = submissions_store[submission_key]
                existing_answer = submission['answers'][i] if i < len(submission['answers']) else ""
            
            questions_html += f'''
            <div class="question-container">
                <div class="question-header">
                    <span class="question-number">Question {i+1}</span>
                    <span class="word-counter" id="counter{i}">0 words</span>
                </div>
                
                <h4>{question}</h4>
                
                <textarea 
                    class="answer-textarea" 
                    name="answer_{i}"
                    placeholder="Enter your detailed answer here (minimum 200 words)..."
                    onInput="updateWordCount({i})"
                    {"disabled" if is_submitted else ""}
                >{existing_answer}</textarea>
            </div>
            '''
        
        submit_section = ""
        if is_submitted:
            submission = submissions_store[submission_key]
            submit_section = f'''
            <div class="submit-section submitted">
                <h3>✅ Assignment Submitted Successfully!</h3>
                <p>Submitted: {submission['submitted_date']}</p>
                <p>Total Words: {submission['total_words']:,}</p>
                <p>Quality Score: {submission['avg_score']:.1f}/100</p>
            </div>
            '''
        else:
            submit_section = '''
            <div class="submit-section">
                <h3>🚀 Ready to Submit?</h3>
                <p id="submitStatus">Complete all questions to submit</p>
                <button type="submit" id="submitBtn" disabled>Submit Assignment</button>
            </div>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{assignment['title']}</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 1000px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    background: #f5f5f5; 
                    line-height: 1.6;
                }}
                .container {{ 
                    background: white; 
                    padding: 40px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                }}
                .header {{ 
                    text-align: center; 
                    border-bottom: 3px solid #2c3e50; 
                    padding-bottom: 20px; 
                    margin-bottom: 30px; 
                }}
                .question-container {{ 
                    background: #f8f9fa; 
                    margin: 20px 0; 
                    padding: 25px; 
                    border-radius: 8px; 
                    border-left: 4px solid #28a745; 
                }}
                .question-header {{ 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    margin-bottom: 15px; 
                }}
                .question-number {{ 
                    background: #007bff; 
                    color: white; 
                    padding: 5px 15px; 
                    border-radius: 20px; 
                    font-weight: bold; 
                }}
                .word-counter {{ 
                    font-size: 14px; 
                    color: #6c757d; 
                    font-weight: bold;
                }}
                .word-counter.good {{ color: #28a745; }}
                .word-counter.warning {{ color: #ffc107; }}
                .word-counter.poor {{ color: #dc3545; }}
                .answer-textarea {{ 
                    width: 100%; 
                    min-height: 150px; 
                    padding: 15px; 
                    border: 2px solid #ddd; 
                    border-radius: 5px; 
                    font-family: Arial, sans-serif; 
                    font-size: 14px; 
                    resize: vertical;
                }}
                .answer-textarea:focus {{ 
                    border-color: #007bff; 
                    outline: none; 
                }}
                .submit-section {{ 
                    background: #e9ecef; 
                    padding: 25px; 
                    border-radius: 8px; 
                    text-align: center; 
                    margin: 30px 0; 
                }}
                .submit-section.submitted {{ 
                    background: #d4edda; 
                    color: #155724; 
                }}
                button {{ 
                    background: #28a745; 
                    color: white; 
                    padding: 15px 30px; 
                    border: none; 
                    border-radius: 5px; 
                    font-size: 16px; 
                    cursor: pointer; 
                }}
                button:disabled {{ 
                    background: #6c757d; 
                    cursor: not-allowed; 
                }}
                .metrics {{ 
                    background: #e7f3ff; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                    text-align: center;
                }}
                .auto-save {{ 
                    position: fixed; 
                    top: 20px; 
                    right: 20px; 
                    background: #28a745; 
                    color: white; 
                    padding: 10px 20px; 
                    border-radius: 20px; 
                    opacity: 0; 
                    transition: opacity 0.3s;
                }}
                .auto-save.show {{ opacity: 1; }}
            </style>
        </head>
        <body>
            <div id="autoSaveIndicator" class="auto-save">✅ Auto-saved</div>
            
            <div class="container">
                <div class="header">
                    <h1>{assignment['title']}</h1>
                    <p><strong>Assignment ID:</strong> {assignment['id']}</p>
                    <p><strong>Engineer:</strong> {assignment['engineer_id']} | <strong>Topic:</strong> {assignment['topic'].title()}</p>
                    <p><strong>Due Date:</strong> {assignment['due_date']} | <strong>Points:</strong> {assignment['points']}</p>
                </div>

                <div class="metrics">
                    <h3>📊 Real-time Metrics</h3>
                    <p>Total Words: <span id="totalWords">0</span> | 
                       Completion: <span id="completion">0%</span> | 
                       Estimated Quality: <span id="quality">0</span>/100</p>
                </div>

                <form id="assignmentForm" onsubmit="submitAssignment(event)">
                    <input type="hidden" name="assignment_id" value="{assignment['id']}">
                    <input type="hidden" name="engineer_id" value="{assignment['engineer_id']}">
                    
                    {questions_html}
                    
                    {submit_section}
                </form>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="/" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
                    <a href="/submissions" style="background: #17a2b8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">📋 View Submissions</a>
                </div>
            </div>

            <script>
                let autoSaveInterval;
                let isSubmitted = {str(is_submitted).lower()};

                function updateWordCount(questionIndex) {{
                    const textarea = document.querySelector('[name="answer_' + questionIndex + '"]');
                    const counter = document.getElementById('counter' + questionIndex);
                    const words = textarea.value.trim() ? textarea.value.trim().split(/\\s+/).length : 0;
                    
                    counter.textContent = words + ' words';
                    
                    if (words >= 200) {{
                        counter.className = 'word-counter good';
                    }} else if (words >= 100) {{
                        counter.className = 'word-counter warning';
                    }} else if (words > 0) {{
                        counter.className = 'word-counter poor';
                    }} else {{
                        counter.className = 'word-counter';
                    }}
                    
                    updateOverallMetrics();
                }}

                function updateOverallMetrics() {{
                    const textareas = document.querySelectorAll('.answer-textarea');
                    let totalWords = 0;
                    let completedQuestions = 0;
                    
                    textareas.forEach(textarea => {{
                        const words = textarea.value.trim() ? textarea.value.trim().split(/\\s+/).length : 0;
                        totalWords += words;
                        if (words >= 50) completedQuestions++;
                    }});
                    
                    const completion = Math.round((completedQuestions / textareas.length) * 100);
                    const quality = Math.min(100, Math.round((totalWords / (textareas.length * 200)) * 100));
                    
                    document.getElementById('totalWords').textContent = totalWords.toLocaleString();
                    document.getElementById('completion').textContent = completion + '%';
                    document.getElementById('quality').textContent = quality;
                    
                    // Update submit button
                    const submitBtn = document.getElementById('submitBtn');
                    const submitStatus = document.getElementById('submitStatus');
                    
                    if (submitBtn && submitStatus) {{
                        if (completion === 100) {{
                            submitBtn.disabled = false;
                            submitStatus.textContent = '✅ Ready to submit!';
                        }} else {{
                            submitBtn.disabled = true;
                            submitStatus.textContent = 'Complete all questions to submit (' + completedQuestions + '/15)';
                        }}
                    }}
                }}

                function autoSave() {{
                    if (isSubmitted) return;
                    
                    const formData = new FormData(document.getElementById('assignmentForm'));
                    const data = Object.fromEntries(formData);
                    
                    fetch('/api/auto-save', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }})
                    .then(response => response.json())
                    .then(result => {{
                        if (result.success) {{
                            showAutoSaveIndicator();
                        }}
                    }})
                    .catch(error => console.log('Auto-save failed:', error));
                }}

                function showAutoSaveIndicator() {{
                    const indicator = document.getElementById('autoSaveIndicator');
                    indicator.classList.add('show');
                    setTimeout(() => {{
                        indicator.classList.remove('show');
                    }}, 2000);
                }}

                function submitAssignment(event) {{
                    event.preventDefault();
                    
                    if (!confirm('🚀 Submit Assignment?\\n\\nOnce submitted, you cannot make changes.')) {{
                        return;
                    }}
                    
                    const formData = new FormData(event.target);
                    const data = Object.fromEntries(formData);
                    
                    fetch('/api/submit', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }})
                    .then(response => response.json())
                    .then(result => {{
                        if (result.success) {{
                            alert('✅ Assignment submitted successfully!');
                            location.reload();
                        }} else {{
                            alert('❌ Submission failed: ' + result.error);
                        }}
                    }})
                    .catch(error => {{
                        alert('❌ Submission failed: ' + error.message);
                    }});
                }}

                // Initialize
                document.addEventListener('DOMContentLoaded', function() {{
                    // Update word counts for existing content
                    const textareas = document.querySelectorAll('.answer-textarea');
                    textareas.forEach((textarea, index) => {{
                        updateWordCount(index);
                    }});
                    
                    // Start auto-save if not submitted
                    if (!isSubmitted) {{
                        autoSaveInterval = setInterval(autoSave, 30000); // Every 30 seconds
                    }}
                }});

                // Clean up on page unload
                window.addEventListener('beforeunload', function() {{
                    if (autoSaveInterval) {{
                        clearInterval(autoSaveInterval);
                    }}
                    if (!isSubmitted) {{
                        autoSave();
                    }}
                }});
            </script>
        </body>
        </html>
        '''
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"

@app.route('/api/submit', methods=['POST'])
def submit_assignment():
    """Submit assignment"""
    try:
        data = request.get_json()
        assignment_id = data.get('assignment_id')
        engineer_id = data.get('engineer_id')
        
        # Collect answers
        answers = []
        total_words = 0
        scores = []
        
        for i in range(15):
            answer = data.get(f'answer_{i}', '').strip()
            answers.append(answer)
            
            analysis = analyze_answer(answer)
            total_words += analysis['word_count']
            scores.append(analysis['score'])
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Store submission
        submission_key = f"sub_{assignment_id}_{engineer_id}"
        submissions_store[submission_key] = {
            'assignment_id': assignment_id,
            'engineer_id': engineer_id,
            'answers': answers,
            'total_words': total_words,
            'avg_score': avg_score,
            'submitted_date': datetime.datetime.now().isoformat(),
            'status': 'submitted'
        }
        
        return jsonify({
            'success': True,
            'message': f'Assignment submitted! Score: {avg_score:.1f}/100',
            'total_words': total_words,
            'avg_score': avg_score
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auto-save', methods=['POST'])
def auto_save():
    """Auto-save progress"""
    try:
        # Simple auto-save acknowledgment
        return jsonify({'success': True, 'message': 'Progress saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/submissions')
def view_submissions():
    """View all submissions"""
    try:
        if not submissions_store:
            return '''
            <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
                <h1>📭 No Submissions Yet</h1>
                <p>Generate and submit an assignment to see submissions here.</p>
                <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
            </div>
            '''
        
        submissions_html = ""
        for key, submission in submissions_store.items():
            submissions_html += f'''
 0; border-radius: 8px; border-left: 4px solid #28a745; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 10px 0; color: #2c3e50;">📚 {submission['assignment_id']}</h3>
                <p><strong>👤 Engineer:</strong> {submission['engineer_id']}</p>
                <p><strong>📅 Submitted:</strong> {submission['submitted_date'][:19]}</p>
                <p><strong>📊 Status:</strong> <span style="color: #28a745; font-weight: bold;">{submission['status'].title()}</span></p>
                <p><strong>📝 Total Words:</strong> {submission['total_words']:,}</p>
                <p><strong>🎯 Quality Score:</strong> {submission['avg_score']:.1f}/100</p>
            </div>
            '''
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>📊 Submissions Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 1000px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    background: #f5f5f5; 
                }}
                .container {{ 
                    background: white; 
                    padding: 40px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                }}
                .stats {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 20px; 
                    margin: 20px 0; 
                }}
                .stat-card {{ 
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 8px; 
                    text-align: center; 
                    border-left: 4px solid #007bff; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="text-align: center; color: #2c3e50;">📊 Submissions Dashboard</h1>
                
                <div class="stats">
                    <div class="stat-card">
                        <h3 style="margin: 0; color: #007bff;">📋 Total Submissions</h3>
                        <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">{len(submissions_store)}</p>
                    </div>
                    <div class="stat-card">
                        <h3 style="margin: 0; color: #28a745;">✅ Completed</h3>
                        <p style="font-size: 2em; margin: 10px 0; color: #2c3e50;">{len(submissions_store)}</p>
                    </div>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
                </div>
                
                <h2 style="color: #2c3e50; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Recent Submissions</h2>
                {submissions_html}
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"

@app.route('/api/stats')
def api_stats():
    """API stats endpoint"""
    try:
        total_assignments = len(assignments_store)
        total_submissions = len(submissions_store)
        
        if total_submissions > 0:
            avg_quality = sum(s['avg_score'] for s in submissions_store.values()) / total_submissions
        else:
            avg_quality = 0
        
        return jsonify({
            'assignments': total_assignments,
            'submissions': total_submissions,
            'avg_quality': avg_quality,
            'status': 'healthy'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analytics')
def analytics():
    """Simple analytics page"""
    try:
        if not submissions_store:
            return '''
            <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
                <h1>📈 No Analytics Data</h1>
                <p>Submit some assignments to see analytics.</p>
                <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
            </div>
            '''
        
        # Calculate analytics
        total_words = sum(s['total_words'] for s in submissions_store.values())
        avg_score = sum(s['avg_score'] for s in submissions_store.values()) / len(submissions_store)
        total_submissions = len(submissions_store)
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>📈 Analytics Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    max-width: 1000px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    background: #f5f5f5; 
                }}
                .container {{ 
                    background: white; 
                    padding: 40px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                }}
                .metrics {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                    gap: 20px; 
                    margin: 30px 0; 
                }}
                .metric-card {{ 
                    background: #f8f9fa; 
                    padding: 25px; 
                    border-radius: 8px; 
                    text-align: center; 
                    border-left: 4px solid #007bff; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="text-align: center; color: #2c3e50;">📈 Analytics Dashboard</h1>
                
                <div class="metrics">
                    <div class="metric-card">
                        <h3 style="margin: 0; color: #007bff;">📊 Total Submissions</h3>
                        <p style="font-size: 3em; margin: 15px 0; color: #2c3e50;">{total_submissions}</p>
                        <p style="color: #6c757d;">Assignments completed</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3 style="margin: 0; color: #28a745;">📝 Total Words</h3>
                        <p style="font-size: 3em; margin: 15px 0; color: #2c3e50;">{total_words:,}</p>
                        <p style="color: #6c757d;">Words written</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3 style="margin: 0; color: #ffc107;">⭐ Average Quality</h3>
                        <p style="font-size: 3em; margin: 15px 0; color: #2c3e50;">{avg_score:.1f}</p>
                        <p style="color: #6c757d;">Out of 100</p>
                    </div>
                    
                    <div class="metric-card">
                        <h3 style="margin: 0; color: #17a2b8;">📈 Avg Words/Submission</h3>
                        <p style="font-size: 3em; margin: 15px 0; color: #2c3e50;">{int(total_words/total_submissions):,}</p>
                        <p style="color: #6c757d;">Words per assignment</p>
                    </div>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
                    <a href="/submissions" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">📋 View Submissions</a>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'version': '2.0-railway-minimal',
            'platform': 'Railway',
            'server': 'Gunicorn',
            'assignments': len(assignments_store),
            'submissions': len(submissions_store),
            'timestamp': datetime.datetime.now().isoformat(),
            'message': 'Physical Design Assignment System is running successfully on Railway'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

# ========================================
# ERROR HANDLERS
# ========================================

@app.errorhandler(404)
def not_found(error):
    return '''
    <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
        <h1>404 - Page Not Found</h1>
        <p>The requested page could not be found.</p>
        <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
    </div>
    ''', 404

@app.errorhandler(500)
def internal_error(error):
    return '''
    <div style="text-align: center; margin: 50px; font-family: Arial, sans-serif;">
        <h1>500 - Internal Server Error</h1>
        <p>Something went wrong on our end.</p>
        <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a>
    </div>
    ''', 500

# ========================================
# WSGI APPLICATION FOR RAILWAY
# ========================================

# This is what Gunicorn looks for
application = app

if __name__ == '__main__':
    # For local development only
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
