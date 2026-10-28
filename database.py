import sqlite3
import os

DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # HR Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS HR_Users (
            hr_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Seed HR Default
    c.execute("INSERT OR IGNORE INTO HR_Users (username, password) VALUES ('admin', 'admin123')")

    # Candidates Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            interview_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Questions Table - Added topic
    c.execute('''
        CREATE TABLE IF NOT EXISTS Questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            question_text TEXT NOT NULL,
            expected_answer TEXT NOT NULL,
            required_skills TEXT NOT NULL
        )
    ''')
    
    # Responses Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Responses (
            response_id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            question_id INTEGER,
            transcript TEXT,
            relevance_score REAL,
            communication_score REAL,
            confidence_score REAL,
            final_score REAL,
            focus_violations INTEGER DEFAULT 0,
            filler_words_count INTEGER DEFAULT 0,
            FOREIGN KEY (candidate_id) REFERENCES Candidates (candidate_id),
            FOREIGN KEY (question_id) REFERENCES Questions (question_id)
        )
    ''')
    
    # Seed Data for Questions if empty
    c.execute("SELECT COUNT(*) FROM Questions")
    if c.fetchone()[0] == 0:
        sample_questions = [
            # Web Development
            ("Web Development", "Explain REST APIs and how they work.", "REST APIs are architectural styles for designing networked applications. They use HTTP requests to access and use data. Operations include GET, POST, PUT, DELETE.", "REST API, HTTP, JSON, Client-server architecture, methods"),
            ("Web Development", "What is the Virtual DOM in React?", "The Virtual DOM is a lightweight copy of the actual DOM. React uses it to improve performance by updating only the changed parts of the real DOM.", "Virtual DOM, React, performance, rendering, UI, efficient"),
            ("Web Development", "Explain the difference between block and inline elements in HTML.", "Block elements take up the full width available and start on a new line. Inline elements only take up as much width as necessary and do not start on a new line.", "block, inline, width, new line, css"),
            ("Web Development", "What is CORS in web development?", "Cross-Origin Resource Sharing (CORS) is a security mechanism that allows or restricts requested resources on a web server depending on where the HTTP request was initiated.", "CORS, security, cross-origin, headers, API"),
            ("Web Development", "Explain closure in JavaScript.", "A closure is a feature in JavaScript where an inner function has access to the outer function's scope even after the outer function has returned.", "closure, scope, javascript, inner function, reference"),
            
            # Machine Learning
            ("Machine Learning", "What is overfitting and how can you prevent it?", "Overfitting occurs when a model learns the training data too well, including noise, and performs poorly on unseen data. It can be prevented using cross-validation, regularization, or gathering more data.", "Overfitting, generalization, cross-validation, regularization, dropout"),
            ("Machine Learning", "Explain the difference between supervised and unsupervised learning.", "Supervised learning uses labeled data to train models to predict outcomes. Unsupervised learning uses unlabeled data to find hidden patterns or groupings.", "Supervised, unsupervised, labeled data, unlabeled data, clustering, classification"),
            ("Machine Learning", "What is the Bias-Variance tradeoff?", "The bias-variance tradeoff is a property of models. High bias implies a model is too simple and underfits. High variance implies the model is too complex and overfits. Good models balance both.", "bias, variance, tradeoff, underfitting, overfitting"),
            ("Machine Learning", "How does a Random Forest algorithm work?", "Random Forest is an ensemble learning method that builds multiple decision trees during training and merges them together to get a more accurate and stable prediction.", "Random Forest, ensemble, decision trees, aggregate, prediction"),
            ("Machine Learning", "What are Activation Functions in Neural Networks?", "Activation functions introduce non-linear properties to neural networks, allowing them to learn complex patterns. Examples include ReLU, Sigmoid, and Tanh.", "Activation function, non-linear, neural networks, ReLU, Sigmoid"),
            
            # Python Programming
            ("Python Programming", "What is the difference between a list and a tuple in Python?", "A list is mutable, meaning it can be changed after creation. A tuple is immutable. Lists are defined with square brackets, tuples with parentheses.", "mutable, immutable, arrays, Python, syntax"),
            ("Python Programming", "How does Python's garbage collection work?", "Python uses reference counting and a cyclic garbage collector to manage memory and free up objects that are no longer in use.", "Garbage collection, reference counting, memory management, objects"),
            ("Python Programming", "What are Python decorators?", "A decorator is a design pattern in Python that allows a user to add new functionality to an existing object without modifying its structure.", "decorator, wrapper, function, modify, structure"),
            ("Python Programming", "Explain list comprehension in Python with an example.", "List comprehension offers a shorter syntax when you want to create a new list based on the values of an existing list. Example: [x for x in fruits if 'a' in x]", "list comprehension, syntax, loop, condition, concise"),
            ("Python Programming", "What is the GIL in Python?", "The Global Interpreter Lock (GIL) is a mutex that protects access to Python objects, preventing multiple threads from executing Python bytecodes at once.", "GIL, Global Interpreter Lock, threads, mutex, concurrency")
        ]
        c.executemany("INSERT INTO Questions (topic, question_text, expected_answer, required_skills) VALUES (?,?,?,?)", sample_questions)
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
