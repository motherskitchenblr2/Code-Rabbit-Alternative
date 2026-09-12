# =============================================================================
# Deterministic static-analysis rules (no AI/agents required)
# =============================================================================
# Curated, rule-based checks that mirror GitHub Enterprise-grade scanners:
#   - secret / credential detection
#   - security anti-patterns (eval, shell=True, raw SQL, weak crypto)
#   - bug smells (bare except, mutable defaults, == None)
#   - dependency vulnerabilities (pinned versions checked against the OSV DB)
#   - repo health / best practices (CI, README, license, lockfiles)
# Each check is a fast, deterministic regex/heuristic -- fully offline except
# the OSV dependency lookups, which bail gracefully when the network is down.
# =============================================================================

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import requests as http_client
except ImportError:  # pragma: no cover
    http_client = None

OSV_ENDPOINT = "https://api.osv.dev/v1/query"
OSV_MAX_QUERIES = 24
OSV_TIMEOUT = 6

SEVERITIES = ("critical", "high", "medium", "low", "info")
CATEGORIES = ("secret", "vulnerability", "security", "bug", "dependency", "best_practice")

# Files never scanned as code (vendored/build output).
SKIPPED_PREFIXES = (
    "node_modules/", "dist/", "build/", ".git/", "vendor/",
    "__pycache__/", "out/", "target/", ".venv/", "venv/",
    "third_party/", ".yarn/", "coverage/",
)
SKIPPED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".pdf",
    ".woff", ".woff2", ".ttf", ".eot", ".zip", ".gz", ".tar", ".min.js",
    ".min.css", ".map", ".lock", ".ipa", ".apk", ".class", ".pyc", ".so",
}
# Files whose whole point is to carry placeholder/demo values -- scanning them
# just produces template noise. Real .env files are still scanned.
SKIPPED_FILENAMES = (
    "gitleaks.toml", ".gitleaks.toml",
    ".env.example", ".env.template", ".env.sample", ".env.dev.example",
    ".env.prod.example",
)
# Manifest basenames parsed for dependency auditing (matched at any depth).
MANIFESTS = ("package.json", "requirements.txt", "Gemfile.lock",
             "Pipfile.lock", "go.mod")
LOCKFILES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml",
             "Pipfile.lock", "poetry.lock", "Gemfile.lock")


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# ── rule registry ────────────────────────────────────────────────────────────

def _make(*, rule, category, severity, message, remediation,
          singleline: Optional[str] = None, multiline: Optional[str] = None,
          flags: int = re.IGNORECASE, placeholder_ok: bool = False):
    return {
        "id": rule, "category": category, "severity": severity,
        "message": message, "remediation": remediation,
        "single": re.compile(singleline, flags | re.MULTILINE) if singleline else None,
        "multi": re.compile(multiline, flags | re.MULTILINE) if multiline else None,
        "placeholder_ok": placeholder_ok,
    }


_PLACEHOLDER_VALUES = {
    "changeme", "yourpassword", "your-password", "your_password", "password",
    "passw0rd", "secret", "secret1", "example", "sample", "xxxxxx", "xxxx",
    "placeholder", "dummy", "test123", "123456", "12345", "qwerty",
    "${password}", "${api_key}", "${secret}", "todo", "changeit", "changethis",
    "your_token", "${token}", "${api-key}", "${access_token}", "your-api-key",
}


def _looks_like_env_ref(value: str) -> bool:
    v = value.lower()
    if ("os.environ" in v or "process.env" in v or "getenv" in v
            or "settings." in v or "config(" in v or "cfg." in v
            or value.startswith(("{", "$", "[", "(")) or value in ("''", '""')
            or "$" in value):
        return True
    # Documented placeholder phrases that ship in template repos / config samples.
    for frag in ("your-", "your_", "-here", "changeme", "changeit",
                 "placeholder", "example", "dummy", "<secret>", "<password>"):
        if frag in v:
            return True
    return False


# ── text scanning ────────────────────────────────────────────────────────────

_TEXT_RULES: List[Dict[str, Any]] = [
    # Credentials (secrets) -- critical/high
    _make(rule="secret.github_pat", category="secret", severity="critical",
          message="GitHub Personal Access Token (ghp_) committed to source",
          remediation="Revoke the token at github.com/settings/tokens, rotate it, and load it from a secret store / CI variable instead of committing it.",
          singleline=r"\bghp_[0-9A-Za-z]{35,}\b"),
    _make(rule="secret.github_oauth", category="secret", severity="critical",
          message="GitHub OAuth token committed to source",
          remediation="Revoke and rotate the token; never commit OAuth credentials.",
          singleline=r"\bgho_[0-9A-Za-z]{35,}\b"),
    _make(rule="secret.github_app", category="secret", severity="high",
          message="GitHub App token committed to source",
          remediation="Use the GitHub App secret via env/CI variables only.",
          singleline=r"\b(ghu_|ghs_|ghr_)[0-9A-Za-z]{35,}\b"),
    _make(rule="secret.gitlab_pat", category="secret", severity="critical",
          message="GitLab Personal Access Token committed to source",
          remediation="Revoke the token in GitLab settings and rotate it via env variables.",
          singleline=r"\bglpat-[0-9A-Za-z\-_]{20,}\b"),
    _make(rule="secret.aws_access_key", category="secret", severity="critical",
          message="AWS Access Key ID committed to source",
          remediation="Deactivate the key in IAM, rotate credentials, store them in AWS Secrets Manager or env vars.",
          singleline=r"\bAKIA[0-9A-Z]{16}\b"),
    _make(rule="secret.aws_secret_key", category="secret", severity="high",
          message="AWS Secret Access Key pattern found near source",
          remediation="Rotate the credential and move it to a secrets manager.",
          singleline=r"(?i)aws_secret_access_key\s*[=:]\s*[\'\"][0-9A-Za-z/+=]{40}[\'\"]"),
    _make(rule="secret.google_api_key", category="secret", severity="high",
          message="Google API key committed to source",
          remediation="Restrict and rotate the key; load it from env/secret manager.",
          singleline=r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    _make(rule="secret.private_key", category="secret", severity="critical",
          message="Private key material committed to source",
          remediation="Remove the key, rotate it, and store in a secrets manager (never in the repo).",
          singleline=r"-----BEGIN (RSA|EC|OPENSSH|DSA|PGP|ENCRYPTED) PRIVATE KEY-----"),
    _make(rule="secret.slack_token", category="secret", severity="high",
          message="Slack token committed to source",
          remediation="Revoke the app token in Slack and store it in env/CI secrets.",
          singleline=r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b"),
    _make(rule="secret.npm_token", category="secret", severity="high",
          message="npm access token committed to source",
          remediation="Revoke the token on npmjs.com/settings/tokens and use env/CI variables.",
          singleline=r"\bnpm_[0-9A-Za-z]{36}\b"),
    _make(rule="secret.stripe_key", category="secret", severity="critical",
          message="Stripe live secret key committed to source",
          remediation="Rotate the key in the Stripe dashboard; use test keys / env variables in code.",
          singleline=r"\bsk_live_[0-9A-Za-z]{24,}\b"),
    _make(rule="secret.jwt", category="secret", severity="high",
          message="Encoded JWT committed to source -- likely a live session credential",
          remediation="Remove the token; generate JWTs at runtime with a server-held secret.",
          singleline=r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b"),
    _make(rule="secret.db_url_password", category="secret", severity="high",
          message="Database connection string containing a password committed to source",
          remediation="Use a secrets manager / env vars and avoid passwords inside URLs in code.",
          singleline=r"(?i)\b(postgres|mysql|mariadb|mongodb|redis)\+?[a-z]*://[^:\s/<>]+:[^@\s/<>]+@"),
    _make(rule="secret.hardcoded_password", category="secret", severity="medium",
          message="Hardcoded password literal (verify this is not a placeholder)",
          remediation="Load credentials from environment variables or a secret store.",
          singleline=r"(?i)\b[a-z0-9_]*?(password|passwd|pwd)\b\s*[=:]\s*[\'\"][^\'\"]{6,}[\'\"]",
          placeholder_ok=True),
    _make(rule="secret.hardcoded_key", category="secret", severity="medium",
          message="Possible hardcoded API key/secret literal",
          remediation="Prefer environment variables or a secret manager for keys.",
          singleline=r"(?i)\b(api[_-]?key|apikey|api[_-]?secret|access[_-]?token|client[_-]?secret)\s*[=:]\s*[\'\"][^\'\"]{12,}[\'\"]",
          placeholder_ok=True),
    _make(rule="secret.connection_string_password", category="secret", severity="medium",
          message="Credential pair found in a connection/URI string",
          remediation="Keep credentials out of committed URI strings.",
          singleline=r"(?i)\b(basic_auth|credentials|auth)\s*[=:]\s*[\'\"][^:\'\"]+:[^\'\"]+[\'\"]",
          placeholder_ok=True),

    # Security anti-patterns
    _make(rule="security.eval", category="security", severity="high",
          message="Dynamic code execution (eval/exec/Function) -- injection risk",
          remediation="Avoid evaluating dynamic strings; use safe parsers and allow-list logic.",
          singleline=r"\b(eval|exec)\s*\(",
          flags=0),
    _make(rule="security.subprocess_shell", category="security", severity="high",
          message="subprocess invoked with shell=True -- shell injection risk",
          remediation="Prefer argument lists without shell=True; validate all inputs.",
          singleline=r"subprocess\.[A-Za-z_]+\([^\n]*shell\s*=\s*True"),
    _make(rule="security.system_call", category="security", severity="medium",
          message="Raw OS command execution (os.system)",
          remediation="Use subprocess with an argument list and never unsanitized inputs.",
          singleline=r"\bos\.system\s*\("),
    _make(rule="security.pickle", category="security", severity="high",
          message="Unsafe deserialization (pickle/shelve load) of untrusted data",
          remediation="Prefer JSON or a safe deserializer; never unpickle untrusted input.",
          singleline=r"\b(pickle|shelve)\.loads?\s*\("),
    _make(rule="security.sql_concat", category="security", severity="high",
          message="Possibly string-built SQL executed without parameters",
          remediation="Use parameterized queries / ORM instead of string interpolation.",
          multiline=r"(?i)\b(execute|executemany|query|raw_input|\.execute)\s*\(\s*f?[\'\"][^\'\"]{0,60}(select|insert|update|delete|drop|alter)",
          singleline=r"\b(execute|executemany)\([^\n)*]*%s[^\n]*\)"),
    _make(rule="security.weak_hash", category="security", severity="medium",
          message="Weak hash function (MD5/SHA1) used -- not suitable for security",
          remediation="Use SHA-256+ or a password KDF (argon2/bcrypt/scrypt) for credentials.",
          singleline=r"\bhashlib\.(md5|sha1)\s*\("),
    _make(rule="security.insecure_html", category="security", severity="high",
          message="Direct DOM HTML injection (innerHTML / document.write) -- XSS risk",
          remediation="Use textContent / safe templating; escape untrusted data.",
          singleline=r"\b(\.innerHTML\s*=\s*|document\.write\s*\()"),
    _make(rule="security.js_function_ctor", category="security", severity="high",
          message="Function constructor from dynamic strings -- code injection risk",
          remediation="Avoid constructing functions from strings; use safe parsers.",
          singleline=r"\bnew\s+Function\s*\("),
    _make(rule="security.shell_exec_js", category="security", severity="high",
          message="Shell command execution in JS (exec/execSync) -- injection risk",
          remediation="Use spawn with an argument array; avoid string shell execution.",
          singleline=r"\b(exec|execSync)\s*\([^\n]*\"|child_process[\s\S]*(exec|execSync)\s*\("),
    _make(rule="security.http_transport", category="security", severity="low",
          message="Plain HTTP endpoint in use -- data sent in clear text",
          remediation="Use HTTPS endpoints wherever possible.",
          singleline=r"(?i)(base[_-]?url|endpoint|api[_-]?url)\s*[=:]\s*[\'\"]http://"),
    _make(rule="security.weak_crypto_js", category="security", severity="low",
          message="Cryptographic primitive possibly used for security (md5/sha1)",
          remediation="Use SHA-256+ or a vetted crypto library for security purposes.",
          singleline=r'\b(md5|sha1)\s*\(\s*[a-zA-Z_]'),

    # Bug smells
    _make(rule="bug.bare_except", category="bug", severity="medium",
          message="Bare except: hides the original error, makes debugging harder",
          remediation="Catch specific exception types you can handle.",
          singleline=r"^\s*except\s*:$",
          flags=0),
    _make(rule="bug.except_pass", category="bug", severity="low",
          message="Swallowed exception (pass) hides failures",
          remediation="Log the exception or fail loudly instead of silently passing.",
          multiline=r"except[^\n]*:\s*(\n\s*(#[^\n]*)?\n)*\s{4,}pass"),
    _make(rule="bug.mutable_default", category="bug", severity="low",
          message="Mutable default argument shared across calls (classic Python bug)",
          remediation="Use None and build the default inside the function.",
          singleline=r"def\s+[A-Za-z_][\w]*\s*\([^)]*\=\s*(\[\]|\{\}|set\(\))"),
    _make(rule="bug.eq_none", category="bug", severity="low",
          message="Comparison to None with == instead of 'is'",
          remediation="Use 'x is None' / 'x is not None'.",
          singleline=r"[^!=!]==\s*None|None\s*==\s*[^!=!]"),
    _make(rule="bug.todo", category="bug", severity="info",
          message="Unresolved task marker (TODO/FIXME/HACK) left in code",
          remediation="Resolve or track in the issue tracker instead of leaving markers.",
          singleline=r"\b(TODO|FIXME|HACK|XXX)\b(?![a-z])"),
    _make(rule="bug.console_sensitive", category="bug", severity="medium",
          message="Sensitive-looking values logged (console) -- data exposure risk",
          remediation="Never log secrets; use structured logging with redaction.",
          singleline=r"console\.(log|debug|warn)\([^\n]*(password|secret|api[_-]?key|token)"),
    _make(rule="bug.debug_true", category="bug", severity="low",
          message="Debug mode left enabled (debug=True)",
          remediation="Gate debug mode behind an env var, off by default in production.",
          singleline=r"\bdebug\s*=\s*True\b"),

    # Best practices / quality
    _make(rule="practice.hardcoded_secret_key", category="best_practice", severity="high",
          message="Framework secret key hardcoded -- session/JWT signing forgery risk",
          remediation="Read SECRET_KEY from environment / .env, never commit a value.",
          singleline=r"(?i)\bse?cret[_\-]?key\s*=\s*[\'\"][^\'\"]{8,}[\'\"]",
          placeholder_ok=True),
    _make(rule="practice.catch_all_json", category="best_practice", severity="info",
          message="Broad exception handling without logging (except ...: pass)",
          remediation="Handle specific errors and log the failure.",
          singleline=r"except\s+(Exception|BaseException)[^\n]*:\s*(\n\s*)?\s*(pass|continue)"),
]


def _value_of(text: str, pattern: re.Pattern, match: re.Match) -> str:
    """Extract the quoted literal after a key assignment for placeholder checks."""
    quoted = re.search(r"[\'\"]([^\'\"]+)[\'\"]", text[match.start():match.start() + 160])
    return quoted.group(1) if quoted else ""


def scan_text(text: str, path: str, lang: str) -> List[Dict[str, Any]]:
    """Run secret/security/bug/practice rules over one file."""
    findings: List[Dict[str, Any]] = []
    seen: set = set()
    for rule in _TEXT_RULES:
        patterns = [rule["single"], rule["multi"]] if lang != "generic" or rule["category"] == "secret" else []
        for pat in patterns:
            if pat is None:
                continue
            for match in pat.finditer(text):
                if rule["placeholder_ok"]:
                    val = _value_of(text, pat, match)
                    if val.lower() in _PLACEHOLDER_VALUES or _looks_like_env_ref(val):
                        continue
                line = _line_of(text, match.start())
                key = (rule["id"], line)
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "id": rule["id"],
                    "category": rule["category"],
                    "severity": rule["severity"],
                    "file": path,
                    "line": line,
                    "message": rule["message"],
                    "remediation": rule["remediation"],
                })
    return findings


# ── dependency auditing (OSV) ────────────────────────────────────────────────

def _osv_vulns(name: str, ecosystem: str, version: str) -> List[Dict[str, Any]]:
    """Query OSV for a pinned package version. Raises RuntimeError if unreachable."""
    if http_client is None:
        raise RuntimeError("requests library unavailable")
    try:
        resp = http_client.post(
            OSV_ENDPOINT,
            json={"package": {"name": name, "ecosystem": ecosystem}, "version": version},
            timeout=OSV_TIMEOUT)
    except Exception as exc:
        raise RuntimeError(f"OSV unreachable: {exc.__class__.__name__}")
    if resp.status_code == 200:
        return (resp.json() or {}).get("vulns") or []
    raise RuntimeError(f"OSV HTTP {resp.status_code}")


def _osv_severity(vuln: Dict[str, Any]) -> str:
    sev = vuln.get("severity") or []
    if sev and isinstance(sev[0], dict) and sev[0].get("score"):
        try:
            score = float(sev[0]["score"])
        except (TypeError, ValueError):
            score = 0.0
        if score >= 9.0:
            return "critical"
        if score >= 7.0:
            return "high"
        if score >= 4.0:
            return "medium"
        return "low"
    label = (vuln.get("database_specific") or {}).get("severity")
    if isinstance(label, str):
        label = label.lower()
        if label == "critical":
            return "critical"
        if label in ("high",):
            return "high"
        if label in ("moderate", "medium"):
            return "medium"
        if label in ("low",):
            return "low"
    return "medium"


def _pin_version(version: str) -> Optional[str]:
    """Best-effort concrete version from a range string (^1.2.3 -> 1.2.3)."""
    version = (version or "").strip()
    if not version or version.lower() in ("*", "latest", "any", "") or "x" in version.split(".")[-1]:
        return None
    # Skip leading range operators/comparators: ^ ~ >= <= > < =
    while version[:1] in "^~><= ":
        version = version[1:]
    parts = []
    for ch in version:
        if ch.isdigit() or ch == ".":
            parts.append(ch)
        else:
            break
    if not parts:
        return None
    digits = "".join(parts).rstrip(".")
    return digits or None


def scan_manifests(manifests: Dict[str, str], osv_queries: Optional[int] = None) -> List[Dict[str, Any]]:
    """Audit pinned dependencies against the OSV database (best-effort)."""
    findings: List[Dict[str, Any]] = []
    osv_left = (OSV_MAX_QUERIES if osv_queries is None or osv_queries is True
                else max(0, int(osv_queries)))
    osv_failed = False
    deduped: set = set()

    def _add_dep(name: str, version: str, file: str) -> None:
        nonlocal findings, osv_left, osv_failed
        if osv_left <= 0:
            return
        osv_left -= 1
        ecosystem = "npm" if _basename(file) == "package.json" else "PyPI"
        try:
            vulns = _osv_vulns(name, ecosystem, version)
        except RuntimeError:
            osv_failed = True
            return
        for vuln in vulns:
            aliases = [a for a in (vuln.get("aliases") or [])
                       if isinstance(a, str) and a.startswith("CVE-")]
            cve = aliases[0] if aliases else (vuln.get("id") or "OSV")
            key = (name, version, cve)
            if key in deduped:
                continue
            deduped.add(key)
            if len(findings) > 400:
                return
            findings.append({
                "id": "dependency.osv",
                "category": "vulnerability",
                "severity": _osv_severity(vuln),
                "file": file, "line": 0,
                "message": f"{name}@{version} is affected by {cve}",
                "remediation": f"Upgrade '{name}' to a patched version; advisory {vuln.get('id')}.",
                "package": name, "version": version, "advisory": vuln.get("id"),
            })

    # package.json (npm) and requirements.txt (PyPI) — matched at any depth
    json_files = [f for f in manifests if _basename(f) == "package.json"]
    req_files = [f for f in manifests if _basename(f) == "requirements.txt"]

    for f in json_files:
        try:
            pkg = json.loads(manifests[f])
        except ValueError:
            pkg = {}
        for section in ("dependencies", "devDependencies"):
            for name, version in (pkg.get(section) or {}).items():
                if not isinstance(version, str):
                    continue
                pinned = _pin_version(version)
                if pinned is None:
                    findings.append({
                        "id": "dependency.unpinned_npm",
                        "category": "dependency", "severity": "low",
                        "file": f, "line": 0,
                        "message": f"Dependency {name} uses unpinned range '{version}'",
                        "remediation": "Pin an exact version so known-vulnerable releases never slip in.",
                    })
                    continue
                _add_dep(name, pinned, f)

    for f in req_files:
        for raw in manifests[f].splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            name, _, version = line.partition("==")
            name = name.strip().replace("_", "-").lower()
            if not name or not version:
                continue
            _add_dep(name, version.strip().split()[0], f)

    if osv_failed:
        findings.append({
            "id": "dependency.osv_unreachable", "category": "best_practice", "severity": "info",
            "file": "manifests", "line": 0,
            "message": "Dependency vulnerability database (OSV) was unreachable",
            "remediation": "Run the scan again with network access to api.osv.dev for full dependency coverage.",
        })
    return findings


# ── repo health ──────────────────────────────────────────────────────────────

def repo_health(paths: List[str]) -> List[Dict[str, Any]]:
    top = {p.split("/", 1)[0].lower() for p in paths}
    findings: List[Dict[str, Any]] = []

    if not any(p.startswith(".github/workflows") for p in paths):
        findings.append({
            "id": "practice.no_ci", "category": "best_practice", "severity": "low",
            "file": ".github/workflows", "line": 0,
            "message": "No CI workflow found under .github/workflows",
            "remediation": "Add a minimal CI workflow that runs lint, test, and dependency checks on PRs.",
        })
    if not any(p.lower().startswith("readme") for p in paths):
        findings.append({
            "id": "practice.no_readme", "category": "best_practice", "severity": "info",
            "file": "README", "line": 0,
            "message": "Repository has no README",
            "remediation": "Add a README describing install, usage, and contribution.",
        })
    if not any(p.lower().startswith("license") for p in paths):
        findings.append({
            "id": "practice.no_license", "category": "best_practice", "severity": "info",
            "file": "LICENSE", "line": 0,
            "message": "Repository has no LICENSE file",
            "remediation": "Add a LICENSE to declare how the code may be used.",
        })
    names = {_basename(p) for p in paths}
    if "package.json" in names and not names.intersection(LOCKFILES):
        findings.append({
            "id": "practice.no_lockfile", "category": "best_practice", "severity": "medium",
            "file": next(p for p in paths if _basename(p) == "package.json"), "line": 0,
            "message": "package.json present but no lockfile committed",
            "remediation": "Commit package-lock.json / yarn.lock / pnpm-lock.yaml for reproducible builds.",
        })
    return findings


def scan_manifests_public(manifests: Dict[str, str], paths: List[str]) -> List[Dict[str, Any]]:
    """Convenience wrapper: manifest + repo-health findings in one pass (used by tests)."""
    return scan_manifests(manifests) + repo_health(paths)


def _lang_of(path: str) -> str:
    if path.endswith((".py", ".pyw")):
        return "python"
    if path.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
        return "js"
    return "generic"


def _skip_path(path: str, size: int = 0) -> bool:
    lowered = path.lower()
    if not path or any(lowered.startswith(p) for p in SKIPPED_PREFIXES):
        return True
    if any(lowered.endswith(ext) for ext in SKIPPED_EXTENSIONS):
        return True
    if lowered.rstrip("/").split("/")[-1] in SKIPPED_FILENAMES:
        return True
    return size > 1_500_000  # too large to fetch via the contents API