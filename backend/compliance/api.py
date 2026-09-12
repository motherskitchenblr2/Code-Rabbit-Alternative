"""Compliance reporting API.

Exposes the (previously orphaned) `backend.compliance.reports` engine so the
Analytics -> Compliance page can show real, generated assessments instead of
hardcoded mock rows. Assessments are generated on demand for a trailing window
(default 90 days); nothing is fabricated client-side.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from backend.security import require_admin
from backend.compliance.reports import (
    create_compliance_engine,
    ComplianceFramework,
    ComplianceStatus,
)

logger = logging.getLogger(__name__)

compliance_bp = Blueprint("compliance", __name__, url_prefix="/api/v1/compliance")

DEFAULT_FRAMEWORKS: List[ComplianceFramework] = [
    ComplianceFramework.SOC2_TYPE_II,
    ComplianceFramework.ISO27001,
    ComplianceFramework.GDPR,
    ComplianceFramework.HIPAA,
    ComplianceFramework.PCI_DSS,
    ComplianceFramework.OWASP_TOP_10,
]

FRAMEWORK_LABELS: Dict[str, str] = {
    "soc2_type_ii": "SOC 2 Type II",
    "soc2_type_i": "SOC 2 Type I",
    "iso27001": "ISO 27001",
    "gdpr": "GDPR",
    "hipaa": "HIPAA",
    "pci_dss": "PCI DSS",
    "owasp_top_10": "OWASP Top 10",
    "nist_csf": "NIST CSF",
}

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_compliance_engine({})
    return _engine


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _report_summary(report: Any) -> Dict[str, Any]:
    return {
        "framework": report.framework.value,
        "name": FRAMEWORK_LABELS.get(report.framework.value, report.framework.value),
        "status": report.overall_status.value,
        "score": round(report.overall_score, 1),
        "total": report.total_controls,
        "compliant": report.compliant_count,
        "partial": report.partial_count,
        "non_compliant": report.non_compliant_count,
        "not_assessed": report.not_assessed_count,
        "findings": len(report.recommendations),
        "generated_at": _iso(report.generated_at),
        "period_start": _iso(report.period_start),
        "period_end": _iso(report.period_end),
    }


def _control_public(control: Any) -> Dict[str, Any]:
    return {
        "id": control.id,
        "title": control.title,
        "category": control.category,
        "status": control.status.value,
        "evidence": list(control.evidence_files or []),
        "automated_checks": list(control.automated_checks or []),
        "manual_checks": list(control.manual_checks or []),
        "last_tested": _iso(control.last_tested),
        "next_review": _iso(control.next_review),
    }


def _generate(framework: ComplianceFramework, days: int = 90):
    engine = _get_engine()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return engine.generate_report(framework, period_start=start, period_end=end)


def _summary_for(framework: ComplianceFramework, days: int = 90) -> Dict[str, Any]:
    try:
        report = _generate(framework, days)
    except ValueError as exc:  # framework not loaded by the engine
        logger.debug("Compliance framework unavailable: %s", exc)
        return {"framework": framework.value,
                "name": FRAMEWORK_LABELS.get(framework.value, framework.value),
                "status": "not_assessed", "score": 0.0, "total": 0,
                "compliant": 0, "partial": 0, "non_compliant": 0, "not_assessed": 0,
                "findings": 0, "generated_at": None,
                "period_start": None, "period_end": None}
    return _report_summary(report)


@compliance_bp.route("/summary", methods=["GET"])
@require_admin
def compliance_summary():
    """Status + score for every assessed framework in one call."""
    days = _safe_days(request.args.get("days"), default=90)
    reports = [_summary_for(fw, days) for fw in DEFAULT_FRAMEWORKS]
    assessed = [r for r in reports if r["total"] > 0]
    avg_score = round(sum(r["score"] for r in assessed) / len(assessed), 1) if assessed else 0.0
    return jsonify({
        "frameworks": reports,
        "overall": {
            "assessed": len(assessed),
            "total": len(reports),
            "avg_score": avg_score,
            "critical_findings": sum(1 for r in assessed if r["status"] == "non_compliant"),
            "window_days": days,
        },
    })


@compliance_bp.route("/report", methods=["GET"])
@require_admin
def compliance_report():
    """Full detailed assessment for one framework."""
    fw = str(request.args.get("framework", "")).strip().lower()
    days = _safe_days(request.args.get("days"), default=90)
    try:
        framework = ComplianceFramework(fw)
    except ValueError:
        return jsonify({"error": f"unknown framework: {fw}",
                        "options": [f.value for f in DEFAULT_FRAMEWORKS]}), 400
    try:
        report = _generate(framework, days)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({
        **_report_summary(report),
        "executive_summary": report.executive_summary,
        "recommendations": list(report.recommendations),
        "evidence_package": list(getattr(report, "evidence_package", [])),
        "controls": [_control_public(c) for c in report.controls],
    })


def _safe_days(raw: Optional[str], default: int = 90) -> int:
    try:
        return max(1, min(int(float(raw)), 365))
    except (TypeError, ValueError):
        return default


def init_compliance(app) -> None:
    app.register_blueprint(compliance_bp)
    logger.info("Compliance API mounted at /api/v1/compliance")