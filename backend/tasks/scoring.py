from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Set
import math

# default weights (configurable)
DEFAULT_WEIGHTS = {
    "urgency": 0.4,
    "importance": 0.3,
    "effort": 0.15,
    "dependency": 0.15,
}

# helper: compute days until due (negative if past due)
def days_until(due_date):
    if due_date is None:
        return None
    today = date.today()
    return (due_date - today).days

def normalize(value, min_v, max_v):
    if min_v == max_v:
        return 0.0
    return max(0.0, min(1.0, (value - min_v) / (max_v - min_v)))

def detect_circular_dependencies(tasks: List[Dict]) -> List[List[str]]:
    # build adjacency based on id (use title fallback if id missing)
    id_map = {}
    for t in tasks:
        key = str(t.get("id") or t.get("title"))
        id_map[key] = t
    graph = {}
    for key, t in id_map.items():
        deps = []
        for dep in t.get("dependencies", []):
            dep_key = str(dep)
            if dep_key in id_map:
                deps.append(dep_key)
        graph[key] = deps

    visited = set()
    stack = []
    cycles = []

    def dfs(node, path):
        visited.add(node)
        path.append(node)
        for neigh in graph.get(node, []):
            if neigh in path:
                # found cycle
                idx = path.index(neigh)
                cycles.append(path[idx:] + [neigh])
            elif neigh not in visited:
                dfs(neigh, path.copy())

    for n in graph:
        if n not in visited:
            dfs(n, [])
    return cycles

def validate_tasks(tasks: List[Dict]) -> Tuple[List[Dict], List[str]]:
    errors = []
    valid = []
    for i, t in enumerate(tasks):
        t_copy = dict(t)
        # basic defaults and validation
        title = t_copy.get("title")
        if not title:
            errors.append(f"Task at index {i} missing title.")
            continue
        # importance
        imp = t_copy.get("importance")
        try:
            imp = int(imp) if imp is not None else 5
        except Exception:
            imp = 5
        imp = max(1, min(10, imp))
        t_copy["importance"] = imp
        # estimated_hours
        eh = t_copy.get("estimated_hours", 1.0)
        try:
            eh = float(eh)
            if eh <= 0:
                eh = 1.0
        except Exception:
            eh = 1.0
        t_copy["estimated_hours"] = eh
        # due_date
        dd = t_copy.get("due_date")
        if dd in (None, "", "null"):
            t_copy["due_date"] = None
        else:
            if isinstance(dd, str):
                try:
                    t_copy["due_date"] = datetime.strptime(dd, "%Y-%m-%d").date()
                except Exception:
                    errors.append(f"Task '{title}' has invalid due_date '{dd}' (expected YYYY-MM-DD).")
                    t_copy["due_date"] = None
        # dependencies
        deps = t_copy.get("dependencies") or []
        if not isinstance(deps, list):
            deps = [deps]
        t_copy["dependencies"] = [str(d) for d in deps]
        # id
        if "id" not in t_copy:
            t_copy["id"] = str(title)
        valid.append(t_copy)
    return valid, errors

def compute_scores(tasks: List[Dict], weights: Dict = None, strategy: str = "smart") -> List[Dict]:
    if weights is None:
        weights = DEFAULT_WEIGHTS
    # validate & normalize
    tasks, errors = validate_tasks(tasks)
    if errors:
        # attach errors into a dedicated task-level response? For now raise
        # Instead, we'll include errors in returned metadata elsewhere. Here we continue.
        pass

    # prepare arrays for normalization
    days_list = []
    imp_list = []
    effort_list = []
    id_to_task = {}
    for t in tasks:
        id_to_task[str(t["id"])] = t
        d = days_until(t.get("due_date"))
        days_list.append(float(d) if d is not None else 9999.0)
        imp_list.append(float(t["importance"]))
        effort_list.append(float(t["estimated_hours"]))

    # normalization ranges
    min_days = min(days_list) if days_list else 0.0
    max_days = max(days_list) if days_list else 1.0
    min_imp = min(imp_list) if imp_list else 1.0
    max_imp = max(imp_list) if imp_list else 10.0
    min_eff = min(effort_list) if effort_list else 1.0
    max_eff = max(effort_list) if effort_list else max(1.0, min_eff)

    # precompute how many tasks are blocked by each task (dependency centrality)
    blocked_count = {str(t["id"]): 0 for t in tasks}
    for t in tasks:
        for dep in t["dependencies"]:
            dep_key = str(dep)
            if dep_key in blocked_count:
                blocked_count[dep_key] += 1

    results = []
    for t in tasks:
        tid = str(t["id"])
        # urgency score: nearer due date => higher urgency
        d = days_until(t.get("due_date"))
        if d is None:
            # no due date => low urgency
            urgency = 0.0
        else:
            # map days to urgency: negative (past due) => very urgent
            # produce higher score for smaller days value
            # convert days range so that min_days maps to 1 and max_days maps to 0
            urgency = 1.0 - normalize(float(d), min_days, max_days)
            # amplify past-due
            if d < 0:
                urgency = min(1.5, urgency + (abs(d) / 30.0))
        # importance normalized
        importance = normalize(float(t["importance"]), min_imp, max_imp)
        # effort: lower effort should produce higher "quick win" score
        # we invert effort: smaller hours => higher score
        effort = 1.0 - normalize(float(t["estimated_hours"]), min_eff, max_eff)
        # dependencies: tasks that block others should get boost
        dep_score = normalize(blocked_count.get(tid, 0), 0, max(1, max(blocked_count.values()) if blocked_count else 1))
        # combine according to strategy
        if strategy == "fastest":
            w = {"urgency": 0.1, "importance": 0.2, "effort": 0.6, "dependency": 0.1}
        elif strategy == "impact":
            w = {"urgency": 0.15, "importance": 0.7, "effort": 0.05, "dependency": 0.1}
        elif strategy == "deadline":
            w = {"urgency": 0.7, "importance": 0.15, "effort": 0.05, "dependency": 0.1}
        else:  # smart (balanced)
            w = weights

        raw_score = (
            urgency * w.get("urgency", 0)
            + importance * w.get("importance", 0)
            + effort * w.get("effort", 0)
            + dep_score * w.get("dependency", 0)
        )

        # map raw_score to 0-100
        score = max(0.0, min(100.0, raw_score * 100.0))
        # build explanation
        explanation = {
            "urgency": round(urgency, 3),
            "importance": round(importance, 3),
            "effort": round(effort, 3),
            "dependency": round(dep_score, 3),
            "weights": w,
            "raw_score": round(raw_score, 4),
        }
        results.append({
            "id": tid,
            "title": t["title"],
            "due_date": t.get("due_date").isoformat() if t.get("due_date") else None,
            "estimated_hours": t["estimated_hours"],
            "importance": t["importance"],
            "dependencies": t["dependencies"],
            "score": round(score, 2),
            "explanation": explanation,
        })

    # detect cycles and mark tasks in cycles with a flag
    cycles = detect_circular_dependencies(tasks)
    tasks_in_cycles = set()
    for c in cycles:
        for node in c:
            tasks_in_cycles.add(node)
    for r in results:
        if r["id"] in tasks_in_cycles or r["title"] in tasks_in_cycles:
            r.setdefault("meta", {})["circular_dependency"] = True

    # final sort: descending score (higher first), tie-breakers:
    results_sorted = sorted(results, key=lambda x: (-x["score"], x.get("estimated_hours", 0)))
    return results_sorted, cycles
