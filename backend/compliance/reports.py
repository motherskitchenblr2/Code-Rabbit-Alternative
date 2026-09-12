# =============================================================================
# Git-Fix Compliance Reports - SOC2, GDPR, HIPAA, PCI DSS, ISO 27001
# =============================================================================
# Automated compliance reporting for major regulatory frameworks
# =============================================================================

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    SOC2_TYPE_I = "soc2_type_i"
    SOC2_TYPE_II = "soc2_type_ii"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    OWASP_TOP_10 = "owasp_top_10"
    NIST_CSF = "nist_csf"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


@dataclass
class Control:
    id: str
    title: str
    description: str
    framework: ComplianceFramework
    category: str
    status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    evidence: List[str] = field(default_factory=list)
    implementation_notes: str = ""
    responsible_party: str = ""
    last_tested: Optional[datetime] = None
    next_review: Optional[datetime] = None
    evidence_files: List[str] = field(default_factory=list)
    automated_checks: List[str] = field(default_factory=list)
    manual_checks: List[str] = field(default_factory=list)


@dataclass
class ComplianceReport:
    framework: ComplianceFramework
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    overall_status: ComplianceStatus
    overall_score: float
    total_controls: int
    compliant_count: int
    partial_count: int
    non_compliant_count: int
    not_assessed_count: int
    controls: List[Control] = field(default_factory=list)
    executive_summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    evidence_package: List[str] = field(default_factory=list)


class ComplianceEngine:
    """Automated compliance reporting engine"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.controls: Dict[str, Control] = {}
        self.reports: Dict[str, ComplianceReport] = {}
        self._load_frameworks()

    def _load_frameworks(self):
        """Load all compliance framework controls"""
        self._load_soc2_controls()
        self._load_gdpr_controls()
        self._load_hipaa_controls()
        self._load_pci_dss_controls()
        self._load_iso27001_controls()
        self._load_owasp_controls()

    def _load_soc2_controls(self):
        """Load SOC 2 Type II controls (Trust Services Criteria)"""
        soc2_controls = [
            # CC1.0 - Control Environment
            Control(
                id="CC1.1",
                title="Integrity and Ethical Values",
                description="The entity demonstrates a commitment to integrity and ethical values.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Control Environment",
                automated_checks=["check_code_of_conduct", "check_ethics_training"],
                manual_checks=["review_code_of_conduct", "verify_ethics_training_completion"],
            ),
            Control(
                id="CC1.2",
                title="Board Independence",
                description="The board demonstrates independence from management.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Control Environment",
            ),
            # CC2.0 - Communication and Information
            Control(
                id="CC2.1",
                title="Communication of Objectives",
                description="Communication of objectives, responsibilities, and authorities.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Communication and Information",
            ),
            # CC3.0 - Risk Assessment
            Control(
                id="CC3.1",
                title="Risk Identification and Analysis",
                description="Specifies objectives and identifies risks to achievement.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Risk Assessment",
                automated_checks=["check_risk_register", "verify_risk_assessment"],
            ),
            # CC4.0 - Monitoring
            Control(
                id="CC4.1",
                title="Ongoing Monitoring",
                description="Ongoing evaluations of internal control components.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Monitoring",
                automated_checks=["check_monitoring_config", "verify_alerting_rules"],
            ),
            # CC5.0 - Control Activities
            Control(
                id="CC5.1",
                title="Control Selection and Development",
                description="Selects and develops control activities to mitigate risks.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Control Activities",
            ),
            # CC6.0 - Logical Access Controls (Key for code review)
            Control(
                id="CC6.1",
                title="Logical Access Security",
                description="Implements logical access security measures.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Logical Access",
                automated_checks=["check_mfa_enforcement", "verify_rbac", "check_access_reviews"],
            ),
            Control(
                id="CC6.2",
                title="Authentication & Authorization",
                description="Identifies and authenticates users; authorizes access.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Logical Access",
                automated_checks=["check_mfa_enforcement", "verify_rbac", "check_session_management"],
            ),
            Control(
                id="CC6.2",
                title="Network Security",
                description= "Restricts network access to authorized users.",
                framework=ComplianceFramework.SOC2_TYPE_II,
                category="Logical Access",
                automated_checks=["check_network_segmentation", "verify_firewall_rules"],
            ),
            Control(
                id="CC6.3",
                title= "Data Encryption",
                description= "Encrypts data at rest and in transit.",
                framework= ComplianceFramework.SOC2_TYPE_II,
                category= "Logical Access",
                automated_checks= ["check_encryption_at_rest", "verify_tls_config", "check_key_management"],
            ),
            # CC7.0 - System Operations
            Control(
                id="CC7.1",
                title= "System Monitoring",
                description= "Monitors system components for anomalies.",
                framework= ComplianceFramework.SOC2_TYPE_II,
                category= "System Operations",
                automated_checks= ["check_monitoring_config", "verify_alerting", "check_logging"],
            ),
            Control(
                id= "CC7.2",
                title= "Incident Response",
                description= "Detects and responds to security incidents.",
                framework= ComplianceFramework.SOC2_TYPE_II,
                category= "System Operations",
                automated_checks= ["check_incident_response_plan", "verify_alerting"],
            ),
            # CC8.0 - Change Management
            Control(
                id= "CC8.1",
                title= "Change Management",
                description= "Authorizes, designs, develops, and implements changes.",
                framework= ComplianceFramework.SOC2_TYPE_II,
                category= "Change Management",
                automated_checks= ["check_change_management", "verify_code_review", "check_ci_cd"],
            ),
        ]
        for control in soc2_controls:
            self.controls[control.id] = control

    def _load_gdpr_controls(self):
        """Load GDPR Article requirements"""
        gdpr_controls = [
            Control(
                id="GDPR-5",
                title="Principles of Data Processing",
                description="Lawfulness, fairness, transparency; purpose limitation; data minimization; accuracy; storage limitation; integrity and confidentiality.",
                framework=ComplianceFramework.GDPR,
                category="Data Processing Principles",
                automated_checks=["check_data_minimization", "verify_purpose_limitation"],
            ),
            Control(
                id="GDPR-6",
                title="Lawfulness of Processing",
                description="Processing is lawful, fair, and transparent.",
                framework=ComplianceFramework.GDPR,
                category="Lawfulness of Processing",
                automated_checks=["check_lawful_basis", "verify_consent_mechanism"],
            ),
            Control(
                id="GDPR-7",
                title="Conditions for Consent",
                description= "Valid consent requirements for data processing.",
                framework= ComplianceFramework.GDPR,
                category= "Consent",
                automated_checks=["verify_consent_records", "check_consent_withdrawal"],
            ),
            Control(
                id="GDPR-12",
                title="Transparent Information",
                description= "Transparent information, communication, and modalities for exercising rights.",
                framework=ComplianceFramework.GDPR,
                category="Data Subject Rights",
                automated_checks=["check_privacy_policy", "verify_rights_portal"],
            ),
            Control(
                id="GDPR-15",
                title="Right of Access",
                description= "Data subject's right to access their personal data.",
                framework= ComplianceFramework.GDPR,
                category= "Data Subject Rights",
                automated_checks=["verify_access_request_process", "check_data_portability"],
            ),
            Control(
                id="GDPR-16",
                title="Right to Rectification",
                description= "Right to rectify inaccurate personal data.",
                framework=ComplianceFramework.GDPR,
                category="Data Subject Rights",
            ),
            Control(
                id="GDPR-17",
                title="Right to Erasure (Right to be Forgotten)",
                description= "Right to erasure of personal data.",
                framework=ComplianceFramework.GDPR,
                category="Data Subject Rights",
                automated_checks=["verify_deletion_process", "check_retention_policies"],
            ),
            Control(
                id="GDPR-25",
                title="Data Protection by Design and by Default",
                description= "Implement appropriate technical and organizational measures.",
                framework= ComplianceFramework.GDPR,
                category= "Data Protection by Design",
                automated_checks=["check_privacy_by_design", "verify_data_minimization"],
            ),
            Control(
                id="GDPR-28",
                title="Processor Obligations",
                description= "Contracts with processors and their obligations.",
                framework=ComplianceFramework.GDPR,
                category="Processor Management",
                automated_checks=["verify_dpa_contracts", "check_subprocessors"],
            ),
            Control(
                id="GDPR-32",
                title="Security of Processing",
                description= "Implement appropriate technical and organizational measures.",
                framework=ComplianceFramework.GDPR,
                category="Security of Processing",
                automated_checks=["check_encryption", "verify_access_controls", "check_pseudonymization"],
            ),
            Control(
                id="GDPR-33",
                title="Notification of Personal Data Breach",
                description= "Notify supervisory authority within 72 hours.",
                framework=ComplianceFramework.GDPR,
                category="Breach Notification",
                automated_checks=["verify_breach_notification_process", "check_72_hour_reporting"],
            ),
            Control(
                id="GDPR-35",
                title="Data Protection Impact Assessment",
                description= "Conduct DPIA for high-risk processing.",
                framework=ComplianceFramework.GDPR,
                category="DPIA",
                automated_checks=["check_dpia_process", "verify_high_risk_assessment"],
            ),
        ]
        for control in gdpr_controls:
            self.controls[control.id] = control

    def _load_hipaa_controls(self):
        """Load HIPAA Security Rule controls"""
        hipaa_controls = [
            Control(
                id="HIPAA-164.308(a)(1)",
                title="Security Management Process",
                description="Implement policies and procedures to prevent, detect, contain, and correct security violations.",
                framework=ComplianceFramework.HIPAA,
                category="Administrative Safeguards",
                automated_checks=["check_risk_analysis", "verify_sanctions_policy"],
            ),
            Control(
                id="HIPAA-164.308(a)(3)",
                title="Workforce Security",
                description= "Ensure workforce members have appropriate access to ePHI.",
                framework=ComplianceFramework.HIPAA,
                category="Administrative Safeguards",
                automated_checks=["check_access_authorization", "verify_access_termination"],
            ),
            Control(
                id="HIPAA-164.308(a)(5)",
                title="Security Awareness and Training",
                description= "Implement security awareness and training program for all workforce members.",
                framework=ComplianceFramework.HIPAA,
                category="Administrative Safeguards",
                automated_checks=["verify_security_training", "check_training_completion"],
            ),
            Control(
                id="HIPAA-164.312(a)(1)",
                title="Access Control",
                description= "Implement technical policies for electronic information systems.",
                framework=ComplianceFramework.HIPAA,
                category="Technical Safeguards",
                automated_checks=["check_unique_user_id", "verify_emergency_access", "check_automatic_logoff"],
            ),
            Control(
                id="HIPAA-164.312(b)",
                title="Audit Controls",
                description= "Implement hardware, software, and procedural mechanisms to record and examine activity.",
                framework=ComplianceFramework.HIPAA,
                category="Technical Safeguards",
                automated_checks=["check_audit_logs", "verify_log_integrity", "check_log_retention"],
            ),
            Control(
                id="HIPAA-164.312(c)(1)",
                title="Integrity Controls",
                description= "Protect ePHI from improper alteration or destruction.",
                framework=ComplianceFramework.HIPAA,
                category="Technical Safeguards",
                automated_checks=["check_data_integrity", "verify_checksums", "check_digital_signatures"],
            ),
            Control(
                id="HIPAA-164.312(e)(1)",
                title="Transmission Security",
                description= "Implement technical security measures to guard against unauthorized access to ePHI transmitted over electronic networks.",
                framework=ComplianceFramework.HIPAA,
                category="Technical Safeguards",
                automated_checks=["check_tls_encryption", "verify_end_to_end_encryption", "check_key_management"],
            ),
        ]
        for control in hipaa_controls:
            self.controls[control.id] = control

    def _load_pci_dss_controls(self):
        """Load PCI DSS v4.0 requirements"""
        pci_controls = [
            Control(
                id="PCI-1",
                title="Firewall Configuration",
                description="Install and maintain network security controls.",
                framework=ComplianceFramework.PCI_DSS,
                category="Network Security",
                automated_checks=["check_firewall_rules", "verify_network_segmentation"],
            ),
            Control(
                id="PCI-2",
                title="Default Passwords",
                description= "Do not use vendor-supplied defaults for system passwords.",
                framework=ComplianceFramework.PCI_DSS,
                category="Network Security",
                automated_checks=["check_default_passwords", "verify_credential_rotation"],
            ),
            Control(
                id="PCI-3",
                title="Stored Cardholder Data",
                description= "Protect stored cardholder data.",
                framework=ComplianceFramework.PCI_DSS,
                category="Data Protection",
                automated_checks=["check_cardholder_data_encryption", "verify_data_retention"],
            ),
            Control(
                id="PCI-4",
                title="Encrypt Transmission",
                description= "Encrypt transmission of cardholder data across open, public networks.",
                framework=ComplianceFramework.PCI_DSS,
                category="Data Protection",
                automated_checks=["check_tls_encryption", "verify_tls_version", "check_certificate_validity"],
            ),
            Control(
                id="PCI-7",
                title="Restrict Access",
                description= "Restrict access to cardholder data by business need-to-know.",
                framework=ComplianceFramework.PCI_DSS,
                category="Access Control",
                automated_checks=["check_rbac", "verify_least_privilege", "check_access_reviews"],
            ),
            Control(
                id="PCI-8",
                title="Identify and Authenticate",
                description= "Identify users and authenticate access to system components.",
                framework=ComplianceFramework.PCI_DSS,
                category="Identification & Authentication",
                automated_checks=["check_mfa", "verify_password_policy", "check_account_lockout"],
            ),
            Control(
                id="PCI-10",
                title="Track and Monitor",
                description= "Track and monitor all access to network resources and cardholder data.",
                framework=ComplianceFramework.PCI_DSS,
                category="Monitoring",
                automated_checks=["check_audit_logs", "verify_log_retention", "check_alerting"],
            ),
            Control(
                id="PCI-12",
                title="Information Security Policy",
                description= "Maintain a policy that addresses information security for all personnel.",
                framework=ComplianceFramework.PCI_DSS,
                category="Information Security Policy",
            ),
        ]
        for control in pci_controls:
            self.controls[control.id] = control

    def _load_iso27001_controls(self):
        """Load ISO 27001:2022 Annex A controls"""
        iso_controls = [
            Control(
                id="A.5.1",
                title="Information Security Policies",
                description="Information security policy and topic-specific policies.",
                framework=ComplianceFramework.ISO27001,
                category="Information Security Policies",
            ),
            Control(
                id="A.5.10",
                title="Acceptable Use of Assets",
                description= "Rules for acceptable use of information assets.",
                framework=ComplianceFramework.ISO27001,
                category="Asset Management",
            ),
            Control(
                id="A.5.12",
                title="Classification of Information",
                description= "Classification of information based on sensitivity.",
                framework=ComplianceFramework.ISO27001,
                category="Asset Management",
            ),
            Control(
                id="A.6.1",
                title="Screening",
                description="Background verification of candidates.",
                framework=ComplianceFramework.ISO27001,
                category="Human Resource Security",
            ),
            Control(
                id="A.8.1",
                title="Inventory of Assets",
                description="Inventory of information and other associated assets.",
                framework=ComplianceFramework.ISO27001,
                category="Asset Management",
                automated_checks=["check_asset_inventory", "verify_asset_classification"],
            ),
            Control(
                id="A.8.2",
                title="Information Classification",
                description= "Classification of information based on sensitivity.",
                framework=ComplianceFramework.ISO27001,
                category="Asset Management",
            ),
            Control(
                id="A.8.3",
                title="Media Handling",
                description= "Procedures for handling removable media.",
                framework=ComplianceFramework.ISO27001,
                category="Asset Management",
            ),
        ]
        for control in iso_controls:
            self.controls[control.id] = control

    def _load_owasp_controls(self):
        """Load OWASP Top 10 2021 controls"""
        owasp_controls = [
            Control(
                id="A01:2021",
                title="Broken Access Control",
                description="Restrictions on what authenticated users are allowed to do are not properly enforced.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Access Control",
                automated_checks=["check_authorization", "verify_rbac", "check_idor"],
            ),
            Control(
                id="A02:2021",
                title="Cryptographic Failures",
                description= "Failures related to cryptography which lead to exposure of sensitive data.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Cryptography",
                automated_checks=["check_encryption", "verify_key_management", "check_tls_config"],
            ),
            Control(
                id="A03:2021",
                title="Injection",
                description= "Injection flaws allow attackers to relay malicious code through an application.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Injection",
                automated_checks=["check_sql_injection", "check_command_injection", "verify_parameterization"],
            ),
            Control(
                id="A04:2021",
                title="Insecure Design",
                description= "Missing or ineffective control design.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Architecture",
            ),
            Control(
                id="A05:2021",
                title="Security Misconfiguration",
                description= "Security misconfiguration is the most commonly seen issue.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Configuration",
                automated_checks=["check_security_headers", "verify_default_configs", "check_exposed_services"],
            ),
            Control(
                id="A06:2021",
                title="Vulnerable and Outdated Components",
                description= "Components with known vulnerabilities.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Supply Chain",
                automated_checks=["check_dependency_vulnerabilities", "verify_sbom", "check_component_versions"],
            ),
            Control(
                id="A07:2021",
                title="Identification and Authentication Failures",
                description= "Confirmation of user's identity, authentication, and session management.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Authentication",
                automated_checks=["check_mfa", "verify_session_management", "check_credential_stuffing_protection"],
            ),
            Control(
                id="A08:2021",
                title="Software and Data Integrity Failures",
                description= "Code and infrastructure integrity verification failures.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Supply Chain",
                automated_checks=["verify_supply_chain", "check_integrity_verification", "check_ci_cd_integrity"],
            ),
            Control(
                id="A09:2021",
                title="Security Logging and Monitoring Failures",
                description= "Insufficient logging, detection, monitoring, and active response.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Monitoring",
                automated_checks=["check_logging", "verify_alerting", "check_incident_response"],
            ),
            Control(
                id="A10:2021",
                title="Server-Side Request Forgery (SSRF)",
                description= "SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL.",
                framework=ComplianceFramework.OWASP_TOP_10,
                category="Server-Side Request Forgery",
                automated_checks=["check_ssrf_protection", "verify_url_validation", "check_outbound_requests"],
            ),
        ]
        for control in owasp_controls:
            self.controls[control.id] = control

    def generate_report(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
        evidence_paths: Optional[List[str]] = None,
    ) -> ComplianceReport:
        """Generate compliance report for a framework"""
        framework_controls = [
            c for c in self.controls.values() if c.framework == framework
        ]

        if not framework_controls:
            raise ValueError(f"No controls found for framework: {framework}")

        # Assess controls (in real implementation, run automated checks)
        for control in framework_controls:
            control.status = self._assess_control(control)
            control.last_tested = datetime.utcnow()
            control.next_review = datetime.utcnow() + timedelta(days=90)

        # Calculate metrics
        total = len(framework_controls)
        compliant = sum(1 for c in framework_controls if c.status == ComplianceStatus.COMPLIANT)
        partial = sum(1 for c in framework_controls if c.status == ComplianceStatus.PARTIAL)
        non_compliant = sum(1 for c in framework_controls if c.status == ComplianceStatus.NON_COMPLIANT)
        not_assessed = sum(1 for c in framework_controls if c.status == ComplianceStatus.NOT_ASSESSED)

        # Calculate overall score (weighted: compliant=1.0, partial=0.5, non_compliant=0.0, not_assessed=0.0)
        score = (compliant * 1.0 + partial * 0.5) / total * 100 if total > 0 else 0

        # Determine overall status
        if non_compliant > 0:
            overall_status = ComplianceStatus.NON_COMPLIANT
        elif partial > 0:
            overall_status = ComplianceStatus.PARTIAL
        elif not_assessed == total:
            overall_status = ComplianceStatus.NOT_ASSESSED
        else:
            overall_status = ComplianceStatus.COMPLIANT

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            framework, total, compliant, partial, non_compliant, not_assessed
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(framework_controls)

        report = ComplianceReport(
            framework=framework,
            report_id=f"compliance-{framework.value}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            overall_status=overall_status,
            overall_score=round(score, 1),
            total_controls=total,
            compliant_count=compliant,
            partial_count=partial,
            non_compliant_count=non_compliant,
            not_assessed_count=not_assessed,
            controls=framework_controls,
            executive_summary=executive_summary,
            recommendations=recommendations,
            evidence_package=evidence_paths or [],
        )

        self.reports[report.report_id] = report
        return report

    def _assess_control(self, control: Control) -> ComplianceStatus:
        """Assess a single control (in production, run automated checks)"""
        # In production, run automated checks defined in control.automated_checks
        # For now, simulate assessment based on configuration
        if control.automated_checks:
            # Simulate check results
            import random
            rand = hash(control.id) % 100
            if rand < 70:
                return ComplianceStatus.COMPLIANT
            elif rand < 90:
                return ComplianceStatus.PARTIAL
            else:
                return ComplianceStatus.NON_COMPLIANT
        return ComplianceStatus.NOT_ASSESSED

    def _generate_executive_summary(
        self,
        framework: ComplianceFramework,
        total: int,
        compliant: int,
        partial: int,
        non_compliant: int,
        not_assessed: int,
    ) -> str:
        status_text = {
            ComplianceStatus.COMPLIANT: "Compliant",
            ComplianceStatus.PARTIAL: "Partially Compliant",
            ComplianceStatus.NON_COMPLIANT: "Non-Compliant",
            ComplianceStatus.NOT_ASSESSED: "Not Assessed",
        }

        summary = f"""
Executive Summary - {framework.value.upper()} Compliance Report

**Overall Assessment**: {compliant}/{total} controls fully compliant ({(compliant/len(self.controls)*100):.1f}%)
**Partially Compliant**: {partial} controls
**Non-Compliant**: {non_compliant} controls
**Not Assessed**: {not_assessed} controls

**Key Findings**:
- {self._get_key_findings_summary()}

**Risk Assessment**: {'LOW' if non_compliant == 0 else 'HIGH' if non_compliant > 2 else 'MEDIUM'} risk level based on {non_compliant} non-compliant controls.

**Recommendations**:
1. Prioritize remediation of {non_compliant} non-compliant controls
2. Address {partial} partially compliant controls
3. Complete assessment for {not_assessed} unassessed controls
        """.strip()
        return summary

    def _generate_recommendations(self, controls: List[Control]) -> List[str]:
        recommendations = []
        non_compliant = [c for c in controls if c.status == ComplianceStatus.NON_COMPLIANT]
        partial = [c for c in controls if c.status == ComplianceStatus.PARTIAL]

        if non_compliant:
            recommendations.append(
                f"URGENT: Remediate {len(non_compliant)} non-compliant controls immediately. "
                f"Priority: {[c.id for c in non_compliant[:3]]}"
            )
        if partial:
            recommendations.append(
                f"IMPORTANT: Improve {len(partial)} partially compliant controls. "
                f"Focus on: {[c.id for c in partial[:3]]}"
            )
        recommendations.append(
            "Schedule next compliance review within 90 days"
        )
        recommendations.append(
            "Implement continuous compliance monitoring with automated checks"
        )
        return recommendations

    def _get_key_findings_summary(self) -> str:
        non_compliant = sum(1 for c in self.controls.values() if c.status == ComplianceStatus.NON_COMPLIANT)
        partial = sum(1 for c in self.controls.values() if c.status == ComplianceStatus.PARTIAL)
        return f"{non_compliant} non-compliant, {partial} partially compliant controls identified"

    def export_report(self, report: ComplianceReport, format: str = "json") -> str:
        """Export report in specified format"""
        if format == "json":
            return json.dumps(report.__dict__, default=str, indent=2)
        elif format == "markdown":
            return self._to_markdown(report)
        elif format == "html":
            return self._to_html(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _to_markdown(self, report: ComplianceReport) -> str:
        md = f"""# {report.framework.value.upper()} Compliance Report

**Report ID**: {report.report_id}
**Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
**Period**: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}

## Executive Summary

{report.executive_summary}

## Overall Status: {report.overall_status.value.upper()}

**Overall Score**: {report.overall_score:.1f}%

| Metric | Count |
|--------|-------|
| Total Controls | {report.total_controls} |
| Compliant | {report.compliant_count} |
| Partially Compliant | {report.partial_count} |
| Non-Compliant | {report.non_compliant_count} |
| Not Assessed | {report.not_assessed_count} |

## Control Details

| ID | Title | Category | Status | Evidence |
|------|-------|----------|--------|----------|
"""
        for control in report.controls:
            md += f"| {control.id} | {control.title} | {control.category} | {control.status.value} | {len(control.evidence)} items |\n"

        md += f"""

## Recommendations

"""
        for i, rec in enumerate(report.recommendations, 1):
            md += f"{i}. {rec}\n"

        md += f"""

---

*Report generated on {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}*
*Report ID: {report.report_id}*
"""
        return md

    def _to_html(self, report: ComplianceReport) -> str:
        # Similar to markdown but HTML format
        return f"<html><body><h1>{report.framework.value.upper()} Compliance Report</h1></body></html>"


class ComplianceReporter:
    """High-level compliance reporting interface"""

    def __init__(self, config: Dict[str, Any]):
        self.engine = ComplianceEngine(config)

    def generate_all_reports(
        self,
        period_start: datetime,
        period_end: datetime,
        output_dir: str = "./compliance_reports",
    ) -> Dict[str, ComplianceReport]:
        """Generate reports for all frameworks"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        reports = {}
        for framework in ComplianceFramework:
            try:
                report = self.engine.generate_report(framework, period_start, period_end)
                reports[framework.value] = report

                # Save report
                filepath = os.path.join(output_dir, f"{framework.value}_report.md")
                with open(filepath, "w") as f:
                    f.write(self.engine.export_report(report, "markdown"))

                # Also save JSON
                json_path = os.path.join(output_dir, f"{framework.value}_report.json")
                with open(json_path, "w") as f:
                    json.dump(report.__dict__, f, default=str, indent=2)

                logger.info(f"Generated {framework.value} report: {filepath}")
            except Exception as e:
                logger.error(f"Failed to generate {framework.value} report: {e}")

        # Generate summary dashboard
        self._generate_dashboard(output_dir)
        return reports

    def _generate_dashboard(self, output_dir: str):
        """Generate executive dashboard"""
        dashboard = """# Compliance Dashboard

## Executive Summary

"""
        # Would generate summary across all frameworks
        pass


# Convenience function
def create_compliance_engine(config: Dict[str, Any]) -> ComplianceEngine:
    return ComplianceEngine(config)


def create_compliance_reporter(config: Dict[str, Any]) -> ComplianceReporter:
    return ComplianceReporter(config)


__all__ = [
    "ComplianceEngine",
    "ComplianceReporter",
    "ComplianceFramework",
    "ComplianceStatus",
    "Control",
    "ComplianceReport",
    "Requirement",
    "Evidence",
    "create_compliance_engine",
    "create_compliance_reporter",
]