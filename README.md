Smart Task Analyzer
A lightweight AI-inspired task analysis tool that ranks tasks based on urgency, dependencies, importance, and estimated effort.
Backend is built with Django REST Framework, and the frontend is a clean HTML/JS interface.

Setup Instructions
- Create virtual environment & install dependencies
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

- Run the django server
python manage.py runserver

Your API is now available at:
http://127.0.0.1:8000/api/tasks/


- Open the frontend
frontend/index.html

Scoring Algorithm (How the Analyzer Thinks)
Each task receives a priority score (0–100) based on:

1. Urgency
Calculated from due date proximity.
Closer deadlines → higher urgency → higher score.

2. Importance
Direct 1–10 rating from the user.
Higher importance boosts the score significantly.

3. Effort (Estimated Hours)
Low-effort tasks are often more valuable to complete earlier.
Larger effort slightly reduces score.

4. Dependencies
If a task has prerequisites:
dependency graph is constructed
cycles are detected and reported
dependent tasks receive higher “blocking value”

5. Strategy Modes
Users can pick different scoring strategies:
Smart Balance: balanced weighting of all factors
Fastest Wins: prefer shorter tasks
High Impact: weigh importance heavily
Deadline Driven: urgency > importance

The final score is a weighted combination of these factors, producing a clear ordered priority list.

Design Decisions
1. Separation of Frontend & Backend
Backend handles task logic, scoring, and graph analysis
Frontend handles user input and displays suggestions
This keeps the system modular and easier to extend.

2. Stateless API
The backend does not store tasks; it simply analyzes the payload.
This avoids database complexity and makes the API testable and predictable.

3. Dependency Graph Algorithm
A lightweight graph builder with:
topological sorting
cycle detection
dependency depth scoring
This enables accurate ordering even for complex workflows.

4. Simplicity Over Complexity
The goal is clarity:
No frameworks on frontend (plain JS)
Minimal Django setup
Easy to run in any environment

5. CORS Configuration
Frontend runs on port 5500, backend on 8000 — so CORS is enabled specifically for 127.0.0.1.

Time Breakdown
Backend Development
API endpoints (analyze, suggest): 2 hours
Scoring logic, dependency graph: 1.5 hours
CORS setup, testing: 0.5 hour

Frontend Development
HTML layout & structure: 30 mins
JS to manage tasks, bulk input, rendering: 1.5 hours
Fetch integration + suggestion UI: 1 hour

Testing & Debugging
Cross-origin issues & fetch debugging: 1 hour
JSON validation, handling edge cases: 30 mins

Total time: ~ 8 hours

Improvements for Future Versions
1) User Accounts & Database
2) Visual Dependency Graph
3) AI-based Suggestion Engine
4) Convert to React or Vue app