from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import hashlib
import hmac
import base64
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Pipeline state management
pipeline_state = {
    "current_stage": 0,
    "events_processed": 0,
    "comments_dispatched": 0,
    "reviews_created": 0,
}

# Secret for HMAC validation (matching GitHub App setup)
GITHUB_WEBHOOK_SECRET = "code-rabbit-alternative-secret-key"


# ── Stage 1: Webhook Ingestion ──────────────────────────────────────────────
@app.route("/api/v1/webhook", methods=["POST"])
def webhook():
    """Receive and validate GitHub pull_request webhooks."""
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # HMAC signature validation
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature or not validate_signature(payload, signature):
        return jsonify({"error": "Invalid signature"}), 401

    # Discard bot author events to prevent feedback loops
    if is_bot_author(payload):
        return jsonify({"status": "ignored", "reason": "bot_author"}), 202

    # Generate idempotency key
    repo_id = payload.get("repository", {}).get("id", 0)
    pr_number = payload.get("pull_request", {}).get("number", 0)
    head_sha = payload.get("pull_request", {}).get("head", {}).get("sha", "")
    idempotency_key = f"{repo_id}:{pr_number}:{head_sha}"

    # Enqueue for processing (simulate Redis-backed queue)
    pipeline_state["events_processed"] += 1

    return jsonify({
        "status": "accepted",
        "event_id": idempotency_key,
        "diff_metadata": extract_diff_metadata(payload),
    }), 202


def validate_signature(payload, signature):
    """Validate X-Hub-Signature-256 HMAC-SHA256."""
    mac = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, signature)


def is_bot_author(payload):
    """Check if the PR author is an automated bot."""
    user = payload.get("pull_request", {}).get("user", {})
    return user.get("type") == "Bot"


def extract_diff_metadata(payload):
    """Extract structured diff metadata from the webhook payload."""
    pr = payload.get("pull_request", {})
    return {
        "number": pr.get("number"),
        "base_sha": pr.get("base", {}).get("sha"),
        "head_sha": pr.get("head", {}).get("sha"),
        "diff_url": pr.get("diff_url"),
        "title": pr.get("title"),
    }


# ── Stage 2: Tree-sitter AST Diff Slicing ───────────────────────────────────
@app.route("/api/v1/ast-slice", methods=["POST"])
def ast_slice():
    """Parse unified diff into Tree-sitter AST scopes."""
    data = request.get_json()
    if not data or "diff" not in data:
        return jsonify({"error": "Missing 'diff' field"}), 400

    unified_diff = data["diff"]
    # Simulate Tree-sitter AST parsing
    slices = simulate_ast_parsing(unified_diff)

    return jsonify({
        "status": "success",
        "slices": slices,
        "total_modified_lines": sum(len(s["modified_lines"]) for s in slices),
    })


def simulate_ast_parsing(unified_diff):
    """Simulate Tree-sitter-based AST scope extraction from unified diff."""
    # In a real implementation, this would use tree-sitter WASM grammars
    # For the prototype, we parse hunk headers and identify modified line ranges
    lines = unified_diff.split("\n")
    hunks = []
    current_hunk = None

    for line in lines:
        if line.startswith("@@"):
            # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
            parts = line.split(" ")
            old_info = parts[1].lstrip("-").split(",")
            new_info = parts[2].lstrip("+").split(",")
            old_start = int(old_info[0])
            old_count = int(old_info[1]) if len(old_info) > 1 else 1
            current_hunk = {
                "old_start": old_start,
                "old_count": old_count,
                "modified_lines": [],
            }
            hunks.append(current_hunk)
        elif current_hunk and line.startswith("+"):
            # Added line - track line number offset
            # Simplified: just track that it's modified
            line_num = current_hunk["old_start"] + len(current_hunk["modified_lines"])
            current_hunk["modified_lines"].append(line_num)

    # Group consecutive modified lines into scope units
    scopes = []
    for hunk in hunks:
        if hunk["modified_lines"]:
            scopes.append({
                "file_path": "unknown",  # Would be extracted from context
                "scope_type": "function_definition",
                "name": "unknown_function",
                "start_line": hunk["old_start"],
                "end_line": hunk["old_start"] + hunk["old_count"],
                "modified_lines": hunk["modified_lines"],
            })

    return scopes


# ── Stage 3: Contextual RAG & Caller Graphs ─────────────────────────────────
@app.route("/api/v1/rag", methods=["POST"])
def rag():
    """Inject contextual codebase information into LLM prompts."""
    data = request.get_json()
    if not data or "scope" not in data:
        return jsonify({"error": "Missing 'scope' field"}), 400

    scope = data["scope"]
    context = generate_contextual_knowledge(scope)

    return jsonify({
        "status": "success",
        "context": context,
        "callers": context.get("callers", []),
        "associated_tests": context.get("associated_tests", []),
        "repo_rules": context.get("repo_rules", {}),
    })


def generate_contextual_knowledge(scope):
    """Generate contextual knowledge for an AST scope."""
    file_path = scope.get("file_path", "unknown")
    name = scope.get("name", "unknown_function")
    modified_lines = scope.get("modified_lines", [])

    # Simulated vector DB lookup and caller resolution
    callers = []
    if "auth" in file_path.lower() or "jwt" in name.lower():
        callers = [
            {"file": "api/v1/routes.py", "line": 104, "sample": "verify_session_token(token)"}
        ]

    associated_tests = []
    if "test" in file_path.lower():
        associated_tests = [f"tests/test_{name.lower()}.py:test_{name.lower()}_changed"]

    repo_rules = {}
    # Read .coderabbit.yaml if available
    try:
        with open(".coderabbit.yaml", "r") as f:
            import yaml
            config = yaml.safe_load(f)
            repo_rules = config.get("rules", {}) if config else {}
    except Exception:
        pass

    return {
        "target_symbol": name,
        "callers": callers,
        "associated_tests": associated_tests,
        "repo_rules": repo_rules,
        "dependency_graph": {
            "imports": ["import jwt", "from redis import Redis"],
            "dependents": ["api/v1/middleware.py:15"],
        },
    }


# ── Stage 4: Multi-Agent Critic Ensemble ────────────────────────────────────
@app.route("/api/v1/critique", methods=["POST"])
def critique():
    """Run multi-agent LLM review on diff context."""
    data = request.get_json()
    if not data or "findings" not in data:
        return jsonify({"error": "Missing 'findings' field"}), 400

    # Simulate multi-agent parallel critique
    structured_findings = simulate_critique_ensemble(data["findings"])

    return jsonify({
        "status": "success",
        "findings": structured_findings,
        "confidence_filtered": [f for f in structured_findings if f.get("confidence", 0) >= 0.85],
    })


def simulate_critique_ensemble(initial_findings):
    """Simulate specialized LLM critics: Security, Logic, Test Oracle."""
    findings = []

    for f in initial_findings:
        category = f.get("category", "")

        # Security critic
        if "security" in category.lower() or "inject" in category.lower():
            findings.append({
                "category": "security_vulnerability",
                "severity": "CRITICAL" if "critical" in category.lower() else "HIGH",
                "cwe": "CWE-89" if "sql" in category.lower() else "CWE-79",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": f.get("summary", "Security issue detected"),
                "confidence": 0.95,
                "code_patch": generate_patch_for_line(f.get("start_line", 0), "parameterize_input"),
            })

        # Logic critic
        elif "logic" in category.lower() or "edge" in category.lower() or "nil" in category.lower():
            findings.append({
                "category": "logic_bug",
                "severity": "HIGH",
                "cwe": "CWE-697",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": "Logic edge case or nil pointer risk",
                "confidence": 0.88,
                "code_patch": generate_patch_for_line(f.get("start_line", 0), "add_null_check"),
            })

        # Test oracle
        elif "test" in category.lower() or "coverage" in category.lower():
            findings.append({
                "category": "test_coverage",
                "severity": "MEDIUM",
                "cwe": "N/A",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": "May require new or modified unit tests",
                "confidence": 0.82,
                "code_patch": None,
            })

        # General code-style
        else:
            findings.append({
                "category": "code_style",
                "severity": "LOW",
                "cwe": "N/A",
                "start_line": f.get("start_line", 0),
                "end_line": f.get("end_line", 0),
                "summary": "Code style suggestion (handled by linter)",
                "confidence": 0.65,
                "code_patch": None,
            })

    return findings


def generate_patch_for_line(line_num, patch_type):
    """Generate a code patch suggestion for a given line number."""
    patches = {
        "parameterize_input": 'row := db.QueryRow("SELECT id, name FROM users WHERE email = $1", params)',
        "add_null_check": "if x != nil { return x.method() }",
    }
    return patches.get(patch_type, "// TODO: apply appropriate fix")


# ── Stage 5: GitHub API Post & Conversational Bot ───────────────────────────
@app.route("/api/v1/github/review", methods=["POST"])
def github_review():
    """Dispatch consolidated review comments to GitHub PR."""
    data = request.get_json()
    if not data or "findings" not in data or "pr_number" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    pr_number = data["pr_number"]
    findings = data["findings"]

    # Filter to high-confidence findings only
    high_confidence = [f for f in findings if f.get("confidence", 0) >= 0.85]

    # Build GitHub Review API payload
    comments = []
    for finding in high_confidence:
        comment = {
            "path": finding.get("file_path", "modified_file.go"),
            "line": finding.get("start_line", 0),
            "body": f"**{finding['category'].replace('_', ' ').title()}**: {finding['summary']}",
            "side": "RIGHT",
            "body_html": f"<strong>{finding['category'].replace('_', ' ').title()}</strong>: {finding['summary']}",
        }
        comments.append(comment)

    # Single review dispatch via POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews
    review_payload = {
        "event": "COMMENT",
        "body": f"## Git-Fix Walkthrough\n\nIdentified {len(comments)} finding(s) in this PR.",
        "comments": comments,
    }

    pipeline_state["reviews_created"] += 1
    pipeline_state["comments_dispatched"] += len(comments)

    return jsonify({
        "status": "review_dispatched",
        "pr_number": pr_number,
        "total_findings": len(findings),
        "high_confidence": len(high_confidence),
        "comments_posted": len(comments),
        "review_payload": review_payload,
    })


# ── Conversational reply handler ────────────────────────────────────────────
@app.route("/api/v1/chat/reply", methods=["POST"])
def chat_reply():
    """Handle conversational follow-ups when developers reply to bot comments."""
    data = request.get_json()
    if not data or "comment_id" not in data:
        return jsonify({"error": "Missing 'comment_id' field"}), 400

    # In a real implementation, this would restore thread context from Redis
    # and generate a contextual response
    return jsonify({
        "status": "reply_queued",
        "comment_id": data["comment_id"],
        "response": "I can help regenerate that suggestion or answer follow-up questions about the change.",
    })


# ── Health & status endpoints ───────────────────────────────────────────────
@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "pipeline_stage": pipeline_state["current_stage"]})


@app.route("/api/v1/status", methods=["GET"])
def status():
    return jsonify(pipeline_state)


# ── Run the app ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)