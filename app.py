import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import get_db, init_db
import nlp_module

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Run init DB on startup
if not os.path.exists('database.db'):
    init_db()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    role = request.form.get('role')
    conn = get_db()
    c = conn.cursor()
    
    if role == 'hr':
        username = request.form.get('username')
        password = request.form.get('password')
        
        c.execute("SELECT hr_id FROM HR_Users WHERE username=? AND password=?", (username, password))
        if c.fetchone():
            session['user'] = 'hr'
            return redirect(url_for('dashboard'))
        else:
            return "Invalid HR credentials. Please go back and try again.", 401
            
    elif role == 'candidate':
        name = request.form.get('name')
        email = request.form.get('email')
        topic = request.form.get('topic')
        
        if not email or not name or not topic:
            return "Email, Name, and Topic required to login as Candidate.", 400

        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT candidate_id FROM Candidates WHERE email=?", (email,))
        row = c.fetchone()
        if row:
            cid = row['candidate_id']
        else:
            c.execute("INSERT INTO Candidates (name, email) VALUES (?,?)", (name, email))
            conn.commit()
            cid = c.lastrowid
            
        session['user'] = 'candidate'
        session['candidate_id'] = cid
        session['candidate_name'] = name
        session['topic'] = topic
        return redirect(url_for('interview'))
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if session.get('user') != 'hr':
        return redirect(url_for('index'))
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT c.candidate_id, c.name, c.email, q.topic, 
               COUNT(r.response_id) as questions_answered,
               ROUND(AVG(r.final_score), 2) as overall_score, 
               SUM(r.focus_violations) as total_violations
        FROM Candidates c
        JOIN Responses r ON c.candidate_id = r.candidate_id
        JOIN Questions q ON r.question_id = q.question_id
        GROUP BY c.candidate_id, c.name, q.topic
        ORDER BY MAX(r.response_id) DESC
    ''')
    responses = c.fetchall()
    return render_template('dashboard.html', responses=responses)

@app.route('/interview')
def interview():
    if session.get('user') != 'candidate':
        return redirect(url_for('index'))
    conn = get_db()
    c = conn.cursor()
    
    topic = session.get('topic', 'Web Development')
    
    # Fetch exactly 5 random questions for the chosen topic
    c.execute("SELECT * FROM Questions WHERE topic=? ORDER BY RANDOM() LIMIT 5", (topic,))
    questions = c.fetchall()
    
    # Fallback just in case a topic lacks 5 questions
    if not questions:
        c.execute("SELECT * FROM Questions ORDER BY RANDOM() LIMIT 5")
        questions = c.fetchall()
        
    return render_template('interview.html', questions=questions)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    if session.get('user') != 'candidate':
        return jsonify({'error': 'Unauthorized'}), 401
        
    candidate_id = session['candidate_id']
    question_id = request.form.get('question_id')
    focus_violations = request.form.get('focus_violations', 0)
    
    transcript = ""
    # Check if there is written text
    if 'text_answer' in request.form and request.form.get('text_answer').strip():
        transcript = request.form.get('text_answer')
    # If there is audio
    elif 'audio_file' in request.files:
        audio = request.files['audio_file']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{candidate_id}_{question_id}.wav")
        audio.save(filepath)
        # Speech to Text conversion
        transcript = nlp_module.convert_audio_to_text(filepath)
    
    if not transcript:
        return jsonify({'error': 'No response provided or speech recognition failed.'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT expected_answer, required_skills, topic FROM Questions WHERE question_id=?", (question_id,))
    q_data = c.fetchone()
    
    if not q_data:
        return jsonify({'error': 'Question not found'}), 404
        
    expected_answer = q_data['expected_answer']
    required_skills = q_data['required_skills']
    
    # NLP Analysis
    detected_skills, relevance_score, tone, confidence_score, comm_score, filler_count = nlp_module.analyze_response(
        transcript, expected_answer, required_skills
    )
    
    # Calculate Final Score
    tech_score = relevance_score 
    skill_coverage = min((len(detected_skills) / max(1, len(required_skills.split(',')))), 1.0) * 10
    
    final_score = round((relevance_score * 0.4) + (comm_score * 0.3) + (confidence_score * 0.1) + (skill_coverage * 0.2), 2)
    
    # Hard Gating Logic: Prevent entirely unrelated / random text from scoring free points
    if relevance_score < 2.0:
        final_score = 0.0
    else:
        final_score = max(0.0, min(10.0, final_score))
    
    c.execute('''
        INSERT INTO Responses 
        (candidate_id, question_id, transcript, relevance_score, communication_score, confidence_score, final_score, focus_violations, filler_words_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (candidate_id, question_id, transcript, relevance_score, comm_score, confidence_score, final_score, focus_violations, filler_count))
    conn.commit()
    response_id = c.lastrowid
    
    return jsonify({
        'message': 'Analysis complete',
        'report_url': url_for('report', candidate_id=candidate_id, topic=q_data['topic']),
        'detected_skills': detected_skills
    })

@app.route('/report/<int:candidate_id>/<string:topic>')
def report(candidate_id, topic):
    conn = get_db()
    c = conn.cursor()
    
    # Get overall stats
    c.execute('''
        SELECT c.name, q.topic, 
               ROUND(AVG(r.relevance_score), 2) as avg_relevance,
               ROUND(AVG(r.communication_score), 2) as avg_communication,
               ROUND(AVG(r.confidence_score), 2) as avg_confidence,
               ROUND(AVG(r.final_score), 2) as overall_score,
               SUM(r.focus_violations) as total_violations,
               SUM(r.filler_words_count) as total_fillers
        FROM Candidates c
        JOIN Responses r ON c.candidate_id = r.candidate_id
        JOIN Questions q ON r.question_id = q.question_id
        WHERE c.candidate_id=? AND q.topic=?
        GROUP BY c.candidate_id, c.name, q.topic
    ''', (candidate_id, topic))
    overall = c.fetchone()
    
    if not overall:
        return "Report not found", 404
        
    # Get individual question stats
    c.execute('''
        SELECT r.*, q.question_text 
        FROM Responses r
        JOIN Questions q ON r.question_id = q.question_id
        WHERE r.candidate_id=? AND q.topic=?
        ORDER BY r.response_id ASC
    ''', (candidate_id, topic))
    details = c.fetchall()
        
    return render_template('report.html', overall=overall, details=details)

@app.route('/manage_questions')
def manage_questions():
    if session.get('user') != 'hr':
        return redirect(url_for('index'))
    topic_filter = request.args.get('topic', 'All')
    conn = get_db()
    c = conn.cursor()
    # Get all distinct topics for tabs
    c.execute("SELECT DISTINCT topic FROM Questions ORDER BY topic ASC")
    all_topics = [row['topic'] for row in c.fetchall()]
    if topic_filter and topic_filter != 'All':
        c.execute("SELECT * FROM Questions WHERE topic=? ORDER BY question_id DESC", (topic_filter,))
    else:
        c.execute("SELECT * FROM Questions ORDER BY topic ASC, question_id DESC")
    questions = c.fetchall()
    return render_template('questions.html', questions=questions, all_topics=all_topics, active_topic=topic_filter)

@app.route('/add_question', methods=['POST'])
def add_question():
    if session.get('user') != 'hr':
        return redirect(url_for('index'))
    topic = request.form.get('topic')
    question_text = request.form.get('question_text')
    expected_answer = request.form.get('expected_answer')
    required_skills = request.form.get('required_skills')
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO Questions (topic, question_text, expected_answer, required_skills) VALUES (?, ?, ?, ?)",
              (topic, question_text, expected_answer, required_skills))
    conn.commit()
    active_topic = request.form.get('active_topic', 'All')
    return redirect(url_for('manage_questions', topic=active_topic))

@app.route('/edit_question/<int:q_id>', methods=['POST'])
def edit_question(q_id):
    if session.get('user') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    topic = data.get('topic', '').strip()
    question_text = data.get('question_text', '').strip()
    expected_answer = data.get('expected_answer', '').strip()
    required_skills = data.get('required_skills', '').strip()
    if not (topic and question_text and expected_answer and required_skills):
        return jsonify({'error': 'All fields are required.'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE Questions SET topic=?, question_text=?, expected_answer=?, required_skills=? WHERE question_id=?",
        (topic, question_text, expected_answer, required_skills, q_id)
    )
    conn.commit()
    return jsonify({'message': 'Question updated successfully.'})

@app.route('/delete_question/<int:q_id>', methods=['POST'])
def delete_question(q_id):
    if session.get('user') != 'hr':
        return redirect(url_for('index'))
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM Questions WHERE question_id=?", (q_id,))
    conn.commit()
    active_topic = request.form.get('active_topic', 'All')
    return redirect(url_for('manage_questions', topic=active_topic))

# ── Candidate management ───────────────────────────────────────────────────────

@app.route('/delete_candidate/<int:candidate_id>', methods=['POST'])
def delete_candidate(candidate_id):
    """HR: permanently delete a candidate and all their responses."""
    if session.get('user') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM Responses WHERE candidate_id=?", (candidate_id,))
    c.execute("DELETE FROM Candidates WHERE candidate_id=?", (candidate_id,))
    conn.commit()
    return jsonify({'message': 'Candidate deleted successfully.'})

@app.route('/edit_response/<int:response_id>', methods=['POST'])
def edit_response(response_id):
    """HR: update individual score fields for a single response."""
    if session.get('user') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    try:
        relevance   = float(data.get('relevance_score', 0))
        comm        = float(data.get('communication_score', 0))
        confidence  = float(data.get('confidence_score', 0))
        final       = float(data.get('final_score', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid score values.'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """UPDATE Responses
           SET relevance_score=?, communication_score=?, confidence_score=?, final_score=?
           WHERE response_id=?""",
        (relevance, comm, confidence, final, response_id)
    )
    conn.commit()
    return jsonify({'message': 'Response updated successfully.'})

@app.route('/get_candidate_responses/<int:candidate_id>/<string:topic>')
def get_candidate_responses(candidate_id, topic):
    """HR: fetch all individual responses for a candidate+topic (used by edit modal)."""
    if session.get('user') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT r.response_id, q.question_text, r.transcript,
               r.relevance_score, r.communication_score,
               r.confidence_score, r.final_score,
               r.focus_violations, r.filler_words_count
        FROM Responses r
        JOIN Questions q ON r.question_id = q.question_id
        WHERE r.candidate_id=? AND q.topic=?
        ORDER BY r.response_id ASC
    ''', (candidate_id, topic))
    rows = [dict(r) for r in c.fetchall()]
    return jsonify(rows)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
