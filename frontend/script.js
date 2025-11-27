const tasks = [];

// Theme toggle functionality
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.getElementById('theme-icon');
const themeText = document.getElementById('theme-text');
const html = document.documentElement;

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', savedTheme);
updateThemeButton(savedTheme);

themeToggle.addEventListener('click', () => {
  const currentTheme = html.getAttribute('data-theme');
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  updateThemeButton(newTheme);
});

function updateThemeButton(theme) {
  if (theme === 'dark') {
    themeIcon.textContent = '☀️';
    themeText.textContent = 'Light';
  } else {
    themeIcon.textContent = '🌙';
    themeText.textContent = 'Dark';
  }
}

// Render tasks list
function renderTasks() {
  const list = document.getElementById('tasks-list');
  if (tasks.length === 0) {
    list.innerHTML = '<div class="empty-state">No tasks yet. Add a task to get started!</div>';
    return;
  }

  list.innerHTML = '';
  tasks.forEach((t, idx) => {
    const div = document.createElement('div');
    div.className = 'task';

    const score = t._score ?? null;
    let priorityClass = '';
    let badge = '';

    if (score !== null) {
      if (score >= 70) {
        priorityClass = 'priority-high';
        badge = '<span class="badge badge-high">High Priority</span>';
      } else if (score >= 40) {
        priorityClass = 'priority-medium';
        badge = '<span class="badge badge-medium">Medium Priority</span>';
      } else {
        priorityClass = 'priority-low';
        badge = '<span class="badge badge-low">Low Priority</span>';
      }
    }

    if (priorityClass) div.classList.add(priorityClass);

    div.innerHTML = `
      <div style="flex: 1;">
        <strong>${t.title}${badge}</strong>
        <div class="meta">
          ${t.due_date || 'No due date'} • ⏱${t.estimated_hours}h • Importance: ${t.importance}
          ${t.dependencies && t.dependencies.length ? ' • Dependencies: ' + t.dependencies.join(', ') : ''}
        </div>
      </div>
      <div>
        <button onclick="removeTask(${idx})"> Remove</button>
      </div>
    `;
    list.appendChild(div);
  });
}

// Remove task from list
function removeTask(i) {
  tasks.splice(i, 1);
  renderTasks();
}

// Add single task
document.getElementById('add-task').addEventListener('click', () => {
  const title = document.getElementById('title').value.trim();
  if (!title) return alert('Title required');

  const due_date = document.getElementById('due_date').value || null;
  const estimated_hours = parseFloat(document.getElementById('estimated_hours').value) || 1;
  const importance = parseInt(document.getElementById('importance').value) || 5;

  const dependencies = (document.getElementById('dependencies').value || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);

  tasks.push({
    id: title,
    title,
    due_date,
    estimated_hours,
    importance,
    dependencies
  });

  document.getElementById('title').value = '';
  document.getElementById('dependencies').value = '';
  renderTasks();
});

// Trigger analysis for UI tasks
document.getElementById('analyze').addEventListener('click', async () => {
  if (tasks.length === 0) return alert('No tasks to analyze');
  const strategy = document.getElementById('strategy').value;
  await analyzeTasks(tasks, strategy);
});

// Analyze bulk JSON input
document.getElementById('bulk-analyze').addEventListener('click', async () => {
  const raw = document.getElementById('bulk-json').value.trim();
  if (!raw) return alert('No JSON');
  let arr;

  try {
    arr = JSON.parse(raw);
  } catch (e) {
    return alert('Invalid JSON: ' + e.message);
  }

  const strategy = document.getElementById('strategy').value;
  await analyzeTasks(arr, strategy);
});

// Call backend analyze API
async function analyzeTasks(payloadTasks, strategy = 'smart') {
  showOutput('Analyzing tasks...');

  try {
    const resp = await fetch('http://127.0.0.1:8000/api/tasks/analyze/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tasks: payloadTasks, strategy })
    });

    const data = await resp.json();

    if (!resp.ok) {
      showOutput('Error: ' + JSON.stringify(data));
      return;
    }

    if (Array.isArray(data.tasks)) {
      data.tasks.forEach(t => {
        const found = tasks.find(
          x => String(x.id) === String(t.id) || x.title === t.title
        );
        if (found) found._score = t.score;
      });
      renderTasks();
    }

    renderAnalysisResult(data);

  } catch (e) {
    showOutput('Network/Error: ' + e.message);
  }
}

// Render analysis results
function renderAnalysisResult(data) {
  const out = document.getElementById('output');
  out.innerHTML = '';

  if (data.cycles && data.cycles.length) {
    const c = document.createElement('div');
    c.className = 'card';
    c.innerHTML =
      `<strong>Detected circular dependencies:</strong>
       <pre>${JSON.stringify(data.cycles, null, 2)}</pre>`;
    out.appendChild(c);
  }

  data.tasks.forEach(t => {
    const div = document.createElement('div');
    div.className = 'card';
    
    let scoreBadge = '';
    if (t.score >= 70) scoreBadge = '<span class="badge badge-high">Score: ' + t.score + '</span>';
    else if (t.score >= 40) scoreBadge = '<span class="badge badge-medium">Score: ' + t.score + '</span>';
    else scoreBadge = '<span class="badge badge-low">Score: ' + t.score + '</span>';

    div.innerHTML = `
      <strong>${t.title} ${scoreBadge}</strong>
      <div class="meta">Why: ${explain(t.explanation)}</div>
      <div class="meta">
        Due: ${t.due_date || 'none'} • 
        ${t.estimated_hours}h • 
        Importance: ${t.importance}
      </div>
    `;
    out.appendChild(div);
  });
}

// Human readable explanation
function explain(expl) {
  if (!expl) return 'No explanation available';
  return `Urgency: ${expl.urgency} | Importance: ${expl.importance} | Effort: ${expl.effort} | Dependencies: ${expl.dependency}`;
}

// Display output message
function showOutput(msg) {
  const out = document.getElementById('output');
  out.innerHTML = `<div class="card">${msg}</div>`;
}

// Fetch suggestions
document.getElementById('suggest').addEventListener('click', async () => {
  if (tasks.length === 0)
    return alert('Add tasks first or paste JSON and Analyze first');

  const strategy = document.getElementById('strategy').value;
  const qs = encodeURIComponent(JSON.stringify(tasks));
  const url = `http://127.0.0.1:8000/api/tasks/suggest/?tasks=${qs}&strategy=${strategy}`;

  showOutput('Fetching suggestions...');

  try {
    const resp = await fetch(url);
    const data = await resp.json();

    if (!resp.ok) {
      showOutput('Error: ' + JSON.stringify(data));
      return;
    }

    const out = document.getElementById('output');
    out.innerHTML = '<h3>Top Suggestions</h3>';

    data.tasks.forEach(t => {
      const div = document.createElement('div');
      div.className = 'card';
      div.innerHTML = `
        <strong>${t.title}</strong>
        <span class="badge badge-high">Score: ${t.score}</span>
        <div class="meta">${t.why}</div>
      `;
      out.appendChild(div);
    });

  } catch (e) {
    showOutput('⚠️ Network/Error: ' + e.message);
  }
});

// Initial render
renderTasks();