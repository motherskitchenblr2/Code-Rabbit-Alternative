# =============================================================================
# User interface generator for the Self-Improvement module.
# Produces a live, interactive dashboard the user can open in a browser.
# =============================================================================

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any

from .orchestrator import SelfImprovementEngine

logger = logging.getLogger(__name__)

TERMINAL_BOLD = "\033[1m"
TERMINAL_RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
MUTED = "\033[90m"


def generate_status_report(engine: SelfImprovementEngine) -> str:
    """Build a human-readable status report string."""
    s = engine.status()
    lines = []
    lines.append("=" * 60)
    lines.append(f"{MAGENTA}{TERMINAL_BOLD}  GIT-FIX SELF-IMPROVEMENT ENGINE{TERMINAL_RESET}")
    lines.append("=" * 60)

    uptime = s.get("uptime_seconds", 0)
    lines.append(f"{CYAN}Status:{TERMINAL_RESET} {s['status']}")
    lines.append(f"{CYAN}Uptime:{TERMINAL_RESET} {uptime // 60}m {uptime % 60}s")
    lines.append("")

    mem = s["memory"]
    lines.append(f"{CYAN}{TERMINAL_BOLD}MEMORY{TERMINAL_RESET}")
    lines.append(f"  Total memories: {mem['total_memories']}")
    if mem["by_type"]:
        for t, n in sorted(mem["by_type"].items()):
            lines.append(f"    {t:12s} : {n}")
    lines.append("")

    skills = s["skills"]
    lines.append(f"{GREEN}{TERMINAL_BOLD}SKILLS{TERMINAL_RESET}")
    if skills:
        for sk in skills:
            lines.append(f"  {sk['name']:24s} {sk['level']:>11s}  ({sk['xp']}xp)")
    else:
        lines.append("  No skills practiced yet.")
    lines.append("")

    reflex = s["reflexes"]
    lines.append(f"{YELLOW}{TERMINAL_BOLD}RECOVERY REFLEXES{TERMINAL_RESET}")
    if reflex:
        for r in reflex:
            lines.append(f"  {r['error_type']:18s} {r['strategy']:>10s}  "
                         f"hit={r['hit_rate']:>5s} ({r['hits']}x)")
    else:
        lines.append("  No reflexes learned yet.")
    lines.append("")

    recent = s["recent_errors"]
    lines.append(f"{RED}{TERMINAL_BOLD}RECENT ERRORS{TERMINAL_RESET}")
    if recent:
        for e in recent:
            recovered = "OK " if e["recovered"] else "ESCALATE"
            lines.append(f"  [{recovered}] {e['error_type']:24s} "
                         f"({e['attempts']} tries) {e['message'][:48]}")
    else:
        lines.append("  No errors recorded yet — clean bill of health.")
    lines.append("")

    plan = s.get("improvement_plan", [])
    lines.append(f"{MAGENTA}{TERMINAL_BOLD}IMPROVEMENT PLAN{TERMINAL_RESET}")
    if plan:
        for p in plan:
            lines.append(f"  [{p['priority']}] {p['action']:30s} — {p['reason'][:44]}")
    else:
        lines.append("  Nothing to do — all systems nominal.")
    lines.append("")

    goals = engine.development.get_goals()
    if goals:
        lines.append(f"{GREEN}{TERMINAL_BOLD}GOALS{TERMINAL_RESET}")
        for g in goals:
            lines.append(f"  {g['name']:28s} {g['status']:>10s} "
                         f"({int(g['progress'] * 100)}%)")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def generate_html_dashboard(engine: SelfImprovementEngine) -> str:
    """Full HTML report for browser viewing."""
    s = engine.status()
    report = generate_status_report(engine)

    # Escape for embedding
    import html as html_mod
    report_html = html_mod.escape(report)

    stats_json = json.dumps(s, indent=2).replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Git-Fix Self-Improvement Dashboard</title>
<style>
  :root {{
    --bg:#0a0a0f; --panel:#15151d; --text:#d0d0e0; --muted:#6b6b80;
    --magenta:#ff2e8b; --cyan:#00e5ff; --amber:#ffb800; --green:#00e58a;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text);
         font:15px/1.6 "SF Mono",Menlo,Consolas,monospace; padding:32px 20px; }}
  h1 {{ color:var(--magenta); font-size:26px; letter-spacing:2px;
       text-transform:uppercase; margin-bottom:4px; }}
  h2 {{ color:var(--cyan); font-size:16px; margin:28px 0 8px;
       text-transform:uppercase; letter-spacing:1px; }}
  .wrap {{ max-width:960px; margin:0 auto; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
          gap:14px; margin-top:8px; }}
  .card {{ background:var(--panel); border:1px solid #26263a; border-radius:10px;
          padding:16px 18px; }}
  .card h3 {{ color:var(--amber); font-size:13px; text-transform:uppercase;
             letter-spacing:1px; margin-bottom:8px; }}
  .metric {{ font-size:28px; color:var(--green); font-weight:bold; }}
  .pill {{ display:inline-block; background:#26263a; border-radius:20px;
          padding:2px 12px; margin:2px 4px 2px 0; font-size:12px; }}
  .bar {{ background:#26263a; border-radius:6px; height:8px; margin-top:6px; }}
  .bar > div {{ background:var(--magenta); height:8px; border-radius:6px; }}
  pre {{ background:var(--panel); border:1px solid #26263a; border-radius:10px;
        padding:16px; overflow-x:auto; margin-top:10px; color:var(--cyan); }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  th,td {{ text-align:left; padding:6px 8px; border-bottom:1px solid #26263a; }}
  th {{ color:var(--amber); font-size:12px; text-transform:uppercase; }}
  tr:hover {{ background:#1a1a26; }}
  .ok {{ color:var(--green); }} .warn {{ color:var(--amber); }}
  .bad {{ color:var(--magenta); }}
</style>
</head>
<body>
<div class="wrap">
  <h1>⚡ Git-Fix — Self-Improvement Engine</h1>
  <p style="color:var(--muted)">live status &amp; introspection dashboard</p>

  <h2>Situation</h2>
  <div class="grid">
    <div class="card"><h3>Status</h3>
      <div class="metric">{s['status']}</div>
      <div style="color:var(--muted)">uptime {s['uptime_seconds']//60}m {s['uptime_seconds']%60}s</div>
    </div>
    <div class="card"><h3>Memories</h3>
      <div class="metric">{s['memory']['total_memories']}</div>
      <div style="color:var(--muted)">avg importance {s['memory']['avg_importance']}</div>
    </div>
    <div class="card"><h3>Reflexes</h3>
      <div class="metric">{len(s['reflexes'])}</div>
      <div style="color:var(--muted)">learned recovery patterns</div>
    </div>
    <div class="card"><h3>Skills</h3>
      <div class="metric">{len(s['skills'])}</div>
      <div style="color:var(--muted)">tracked capabilities</div>
    </div>
  </div>

  <h2>Skills</h2>
  <div class="card">
    <table>
      <tr><th>Skill</th><th>Level</th><th>XP</th><th>Prereqs met</th></tr>
      {''.join(f"<tr><td>{html_mod.escape(x['name'])}</td><td>{html_mod.escape(x['level'])}</td>"
                            f"<td>{x['xp']}</td><td>{'✔' if x['prereqs_met'] else '—'}</td></tr>"
                            for x in s['skills']) if s['skills'] else "<tr><td colspan=4 style='color:var(--muted)'>No skills yet — practice something.</td></tr>"}
    </table>
  </div>

  <h2>Goals</h2>
  <div class="card">
    {''.join(f"<div style='margin:10px 0'><div>{html_mod.escape(g['name'])} "
             f"<span class='pill'>{html_mod.escape(g['status'])}</span> "
             f"<span class='pill'>{html_mod.escape(g['target_skill'])}</span></div>"
             f"<div class='bar'><div style='width:{max(0.0, min(g['progress'], 1.0))*100}%'></div></div></div>"
             for g in engine.development.get_goals()) or "<div style='color:var(--muted)'>No goals defined.</div>"}
  </div>

  <h2>Improvement Plan</h2>
  <div class="card">
    <table>
      <tr><th>Priority</th><th>Action</th><th>Why</th></tr>
      {''.join(f"<tr><td>{p['priority']}</td><td>{html_mod.escape(p['action'])}</td>"
                            f"<td style='color:var(--muted)'>{html_mod.escape(p['reason'])}</td></tr>" for p in s.get('improvement_plan',[]))}
    </table>
  </div>

  <h2>Recent Errors</h2>
  <div class="card">
    <table>
      <tr><th>Recovered</th><th>Error</th><th>Attempts</th><th>Message</th></tr>
      {''.join(f"<tr><td class='{'ok' if e['recovered'] else 'bad'}'>"
               f"{'✔ recovered' if e['recovered'] else '✘ escalated'}</td>"
               f"<td>{html_mod.escape(e['error_type'])}</td><td>{e['attempts']}</td>"
               f"<td style='color:var(--muted)'>{html_mod.escape(str(e['message'])[:60])}</td></tr>"
               for e in s['recent_errors']) or "<tr><td colspan=4 style='color:var(--muted)'>No errors — clean bill of health.</td></tr>"}
    </table>
  </div>

  <h2>Raw Snapshot</h2>
  <pre>{stats_json}</pre>
  <p style="color:var(--muted);margin-top:16px">Generated {datetime.utcnow().isoformat()}Z
     — Git-Fix self-improvement engine.</p>
</div>
</body>
</html>"""


def export_snapshot(engine: SelfImprovementEngine, output_dir: Optional[str] = None) -> str:
    """Write the HTML dashboard to disk; returns the file path."""
    out_dir = output_dir or os.path.join(Path_home(), ".gitfix", "dashboards")
    os.makedirs(out_dir, exist_ok=True)
    name = f"self-improvement-{time.strftime('%Y%m%d-%H%M%S')}.html"
    path = os.path.join(out_dir, name)
    with open(path, "w") as f:
        f.write(generate_html_dashboard(engine))
    logger.info(f"Dashboard written to {path}")
    return path


def Path_home() -> str:
    from pathlib import Path
    return str(Path.home())