from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import TaskSerializer
from .scoring import compute_scores, validate_tasks, detect_circular_dependencies
import json
from urllib.parse import unquote
from typing import List, Dict

# a trivial in-memory cache of last analyzed tasks (for GET suggest if no tasks provided)
LAST_ANALYZED = []

class AnalyzeTasksView(APIView):
    """
    POST /api/tasks/analyze/
    Accepts JSON array of tasks and returns them sorted by priority score with explanations.
    Accepts optional JSON body:
      {
        "tasks": [...],
        "strategy": "smart" | "fastest" | "impact" | "deadline",
        "weights": { ... }   # optional custom weights
      }
    """
    def post(self, request):
        payload = request.data
        tasks = payload.get("tasks") if isinstance(payload, dict) else payload
        if tasks is None:
            return Response({"error": "No tasks provided. Provide JSON array or {'tasks': [...]}."}, status=status.HTTP_400_BAD_REQUEST)

        strategy = payload.get("strategy", "smart") if isinstance(payload, dict) else "smart"
        weights = payload.get("weights") if isinstance(payload, dict) else None

        # validate and compute
        # TaskSerializer will ensure fields type
        serializer = TaskSerializer(data=tasks, many=True)
        if not serializer.is_valid():
            return Response({"error": "Invalid task format", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        validated_tasks = serializer.validated_data

        scored, cycles = compute_scores(validated_tasks, weights=weights, strategy=strategy)
        # store last analyzed
        global LAST_ANALYZED
        LAST_ANALYZED = scored
        result = {
            "strategy": strategy,
            "cycles": cycles,
            "tasks": scored
        }
        return Response(result, status=status.HTTP_200_OK)

class SuggestTasksView(APIView):
    """
    GET /api/tasks/suggest/
    Returns top 3 tasks to work on today, with explanations.
    Accepts optional query param 'tasks' as URL-encoded JSON array or uses last analyzed tasks.
    Example: /api/tasks/suggest/?tasks=[{...}]
    Also accepts ?strategy=impact etc.
    """
    def get(self, request):
        tasks_param = request.query_params.get("tasks")
        strategy = request.query_params.get("strategy", "smart")
        tasks = None
        if tasks_param:
            try:
                tasks = json.loads(unquote(tasks_param))
            except Exception as e:
                return Response({"error": "Failed to parse tasks query param as JSON", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            global LAST_ANALYZED
            if LAST_ANALYZED:
                # use last analyzed results (already scored)
                scored = LAST_ANALYZED
                top3 = scored[:3]
                for t in top3:
                    t["why"] = f"Selected by previous analysis (strategy={strategy})."
                return Response({"tasks": top3}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "No tasks provided and no previous analysis available. Provide tasks in 'tasks' query param or POST to /analyze first."}, status=status.HTTP_400_BAD_REQUEST)

        # compute scores on provided tasks
        from .scoring import compute_scores
        scored, cycles = compute_scores(tasks, strategy=strategy)
        top3 = scored[:3]
        # make explanations readable
        for t in top3:
            why = []
            expl = t.get("explanation", {})
            if expl.get("urgency", 0) > 0.6:
                why.append("Urgent due date")
            if expl.get("importance", 0) > 0.6:
                why.append("High importance")
            if expl.get("effort", 0) > 0.6:
                why.append("Quick win (low effort)")
            if expl.get("dependency", 0) > 0.3:
                why.append("Blocks other tasks")
            t["why"] = "; ".join(why) or "Balanced priority"
        return Response({"tasks": top3, "cycles": cycles}, status=status.HTTP_200_OK)
