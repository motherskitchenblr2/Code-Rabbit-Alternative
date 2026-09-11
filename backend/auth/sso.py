# =============================================================================
# Git-Fix Enterprise SSO - SAML/OIDC Authentication & SCIM Provisioning
# =============================================================================
# Enterprise Single Sign-On with SAML 2.0, OIDC, and SCIM 2.0 provisioning
# =============================================================================

import os
import json
import logging
import secrets
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

logger = logging.getLogger(__name__)


class SSOProvider(str, Enum):
    SAML = "saml"
    OIDC = "oidc"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    AUTH0 = "auth0"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GENERIC_OIDC = "generic_oidc"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


@dataclass
class SSOConfig:
    provider: SSOProvider
    entity_id: str
    sso_url: str
    slo_url: Optional[str] = None
    x509_cert: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    issuer: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    scopes: List[str] = field(default_factory=lambda: ["openid", "email", "profile"])
    attribute_mapping: Dict[str, str] = field(default_factory=lambda: {
        "email": "email",
        "first_name": "given_name",
        "last_name": "family_name",
        "name": "name",
        "groups": "groups",
        "roles": "roles",
    })
    allow_idp_initiated: bool = False
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    sign_requests: bool = True
    want_assertions_signed: bool = True
    want_assertions_encrypted: bool = False


@dataclass
class User:
    id: str
    external_id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    emails: List[Dict[str, Any]] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    active: bool = True
    status: UserStatus = UserStatus.ACTIVE
    provider: SSOProvider = SSOProvider.SAML
    external_groups: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


@dataclass
class Group:
    id: str
    display_name: str
    description: Optional[str] = None
    members: List[str] = field(default_factory=list)
    external_id: Optional[str] = None
    provider: SSOProvider = SSOProvider.SAML
    metadata: Dict[str, Any] = field(default_factory=dict)


class SSOManager:
    """Enterprise SSO Manager supporting SAML 2.0, OIDC, and SCIM 2.0"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sso_configs: Dict[str, SSOConfig] = {}
        self.users: Dict[str, User] = {}
        self.groups: Dict[str, Group] = {}
        self._load_configs()

    def _load_configs(self):
        """Load SSO configurations from config"""
        sso_config = self.config.get("sso", {})
        for provider_name, config in sso_config.get("providers", {}).items():
            self.sso_configs[provider_name] = SSOConfig(
                provider=SSOProvider(config.get("provider", "saml")),
                entity_id=config.get("entity_id", ""),
                sso_url=config.get("sso_url", ""),
                slo_url=config.get("slo_url"),
                x509_cert=config.get("x509_cert"),
                client_id=config.get("client_id"),
                client_secret=config.get("client_secret"),
                issuer=config.get("issuer"),
                authorization_endpoint=config.get("authorization_endpoint"),
                token_endpoint=config.get("token_endpoint"),
                userinfo_endpoint=config.get("userinfo_endpoint"),
                jwks_uri=config.get("jwks_uri"),
                scopes=config.get("scopes", ["openid", "email", "profile"]),
                attribute_mapping=config.get("attribute_mapping", {}),
                allow_idp_initiated=config.get("allow_idp_initiated", False),
                name_id_format=config.get("name_id_format", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"),
                sign_requests=config.get("sign_requests", True),
                want_assertions_signed=config.get("want_assertions_signed", True),
                want_assertions_encrypted=config.get("want_assertions_encrypted", False),
            )

    # =============================================================================
    # SAML 2.0 Support
    # =============================================================================

    def build_saml_auth_request(self, provider_name: str, relay_state: Optional[str] = None) -> str:
        """Generate SAML AuthnRequest"""
        config = self.sso_configs.get(provider_name)
        if not config:
            raise ValueError(f"SSO provider {provider_name} not configured")

        request_id = f"_{secrets.token_hex(16)}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build SAML AuthnRequest
        authn_request = ET.Element(
            "{urn:oasis:names:tc:SAML:2.0:protocol}AuthnRequest",
            ID=request_id,
            Version="2.0",
            IssueInstant=issue_instant,
            Destination=config.sso_url,
            AssertionConsumerServiceURL=f"{self.config.get('base_url', '')}/auth/saml/acs",
            ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
        )

        issuer = ET.SubElement(authn_request, "{urn:oasis:names:tc:SAML:2.0:assertion}Issuer")
        issuer.text = config.entity_id

        name_id_policy = ET.SubElement(
            authn_request,
            "{urn:oasis:names:tc:SAML:2.0:protocol}NameIDPolicy",
            Format=config.name_id_format,
            AllowCreate="true",
        )

        requested_authn_context = ET.SubElement(
            authn_request,
            "{urn:oasis:names:tc:SAML:2.0:protocol}RequestedAuthnContext",
            Comparison="exact",
        )
        authn_context_class = ET.SubElement(
            requested_authn_context,
            "{urn:oasis:names:tc:SAML:2.0:assertion}AuthnContextClassRef",
        )
        authn_context_class.text = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"

        if config.allow_idp_initiated:
            authn_request.set("ForceAuthn", "true")

        # Sign the request if configured
        if config.sign_requests and config.x509_cert:
            self._sign_saml_request(authn_request, config.x509_cert)

        # Encode for redirect
        request_xml = tostring(authn_request, encoding="unicode")
        encoded_request = base64.b64encode(request_xml.encode()).decode()

        # Build redirect URL
        params = {
            "SAMLRequest": encoded_request,
        }
        if relay_state:
            params["RelayState"] = relay_state

        auth_url = f"{config.sso_url}?{urlencode(params)}"
        return auth_url

    def _sign_saml_request(self, element: ET.Element, cert: str):
        """Sign SAML request with certificate"""
        # Simplified - in production use xmlsec or similar
        pass

    def parse_saml_response(self, saml_response: str, provider_name: str) -> Optional[User]:
        """Parse SAML Response and extract user"""
        config = self.sso_configs.get(provider_name)
        if not config:
            raise ValueError(f"SSO provider {provider_name} not configured")

        # Decode SAML response
        try:
            decoded = base64.b64decode(saml_response)
            root = ET.fromstring(decoded)
        except Exception as e:
            logger.error(f"Failed to parse SAML response: {e}")
            return None

        # Validate signature if required
        if config.want_assertions_signed:
            if not self._verify_saml_signature(saml_response, config.x509_cert):
                logger.error("SAML response signature validation failed")
                return None

        # Extract user attributes
        user = self._extract_user_from_saml(root, provider_name)
        return user

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _verify_saml_signature(self, saml_response: str, cert: str) -> bool:
        """Verify SAML response signature.

        NOTE: Real verification requires python-xmlsec / lxml path verification,
        which is NOT wired in here. To avoid a fail-open authentication bypass
        (any attacker could forge an assertion), this deliberately fails
        CLOSED unless a signing certificate is present AND a real verifier is
        implemented.
        """
        if not cert:
            logger.error(
                "SAML signature verification requested but no x509 cert configured; denying assertion"
            )
            return False
        logger.error(
            "SAML signature verification is not implemented; denying assertion "
            "(fail-closed — wire python-xmlsec before enabling assertions-signed)"
        )
        return False

    def _extract_user_from_saml(self, root: ET.Element, provider_name: str) -> Optional[User]:
        """Extract user attributes from SAML assertion"""
        # Find Assertion
        assertion = root.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}Assertion")
        if assertion is None:
            return None

        # Extract NameID
        name_id = assertion.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}NameID")
        name_id_value = name_id.text if name_id is not None else ""

        # Extract attributes
        attributes = {}
        for attr in root.findall(".//{urn:oasis:names:tc:SAML:2.0:assertion}Attribute"):
            name = attr.get("Name")
            values = [v.text for v in attr.findall(".//{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue")]
            if values:
                attributes[name] = values[0] if len(values) == 1 else values

        # Map attributes using config mapping
        config = self.sso_configs.get("default", SSOConfig(provider=SSOProvider.SAML, entity_id="", sso_url=""))
        mapping = config.attribute_mapping

        user = User(
            id=f"saml_{secrets.token_hex(8)}",
            external_id=name_id_value,
            email=attributes.get(mapping.get("email", "email"), ""),
            username=attributes.get(mapping.get("username", "username")),
            first_name=attributes.get(mapping.get("first_name", "first_name")),
            last_name=attributes.get(mapping.get("last_name", "last_name")),
            display_name=attributes.get(mapping.get("name", "name")),
            provider=PlatformType.SAML,
        )

        # Parse groups
        groups = attributes.get(mapping.get("groups", "groups"), [])
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.split(",")]
        user.groups = groups

        # Parse roles
        roles = attributes.get(mapping.get("roles", "roles"), [])
        if isinstance(roles, str):
            roles = [r.strip() for r in roles.split(",")]
        user.roles = roles

        return user

    # =============================================================================
    # OIDC / OpenID Connect Support
    # =============================================================================

    async def get_oidc_authorization_url(self, provider_name: str, redirect_uri: str, state: str, nonce: Optional[str] = None) -> str:
        """Generate OIDC authorization URL"""
        config = self.sso_configs.get(provider_name)
        if not config or not config.authorization_endpoint:
            raise ValueError(f"OIDC provider {provider_name} not configured")

        params = {
            "client_id": config.client_id,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if nonce:
            params["nonce"] = nonce

        auth_url = f"{config.authorization_endpoint}?{urlencode(params)}"
        return auth_url

    async def exchange_oidc_code(self, provider_name: str, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        config = self.sso_configs.get(provider_name)
        if not config or not config.token_endpoint:
            raise ValueError(f"OIDC provider {provider_name} not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def get_oidc_userinfo(self, provider_name: str, access_token: str) -> Optional[User]:
        """Get user info from OIDC UserInfo endpoint"""
        config = self.sso_configs.get(provider_name)
        if not config or not config.userinfo_endpoint:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            userinfo = response.json()

        return self._create_user_from_oidc(userinfo, "oidc")

    def _create_user_from_oidc(self, userinfo: Dict[str, Any], provider: str) -> User:
        mapping = self.sso_configs.get(provider, SSOConfig(provider=SSOProvider.OIDC, entity_id="", sso_url="")).attribute_mapping

        user = User(
            id=f"oidc_{secrets.token_hex(8)}",
            external_id=userinfo.get("sub", ""),
            email=userinfo.get(mapping.get("email", "email"), ""),
            username=userinfo.get(mapping.get("username", "preferred_username")),
            first_name=userinfo.get(mapping.get("first_name", "given_name")),
            last_name=userinfo.get(mapping.get("last_name", "family_name")),
            display_name=userinfo.get(mapping.get("name", "name")),
            provider=PlatformType.OIDC,
        )

        # Parse groups
        groups = userinfo.get(mapping.get("groups", "groups"), [])
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.split(",")]
        user.groups = groups

        # Parse roles
        roles = userinfo.get(mapping.get("roles", "roles"), [])
        if isinstance(roles, str):
            roles = [r.strip() for r in roles.split(",")]
        user.roles = roles

        return user

    # =============================================================================
    # SCIM 2.0 Provisioning
    # =============================================================================

    async def scim_create_user(self, provider_name: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user via SCIM 2.0"""
        config = self.sso_configs.get(provider_name)
        if not config:
            raise ValueError(f"SCIM provider {provider_name} not configured")

        # Build SCIM user payload
        scim_user = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": user_data.get("email", ""),
            "name": {
                "givenName": user_data.get("first_name", ""),
                "familyName": user_data.get("last_name", ""),
                "formatted": user_data.get("display_name", ""),
            },
            "emails": [
                {"value": user_data.get("email", ""), "primary": True, "type": "work"}
            ],
            "name": {
                "givenName": user_data.get("first_name", ""),
                "familyName": user_data.get("last_name", ""),
            },
            "active": user_data.get("active", True),
        }

        if "groups" in user_data:
            scim_user["groups"] = [{"value": g} for g in user_data["groups"]]

        # In production, make actual API call to IdP SCIM endpoint
        # For now, return simulated response
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": f"scim_{secrets.token_hex(8)}",
            "userName": user_data.get("email", ""),
            "meta": {
                "resourceType": "User",
                "created": datetime.utcnow().isoformat() + "Z",
                "lastModified": datetime.utcnow().isoformat() + "Z",
            },
        }

    async def scim_update_user(self, provider_name: str, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user via SCIM 2.0 PATCH"""
        # Implement PATCH operation for SCIM
        return {"status": "updated", "id": user_id}

    async def scim_delete_user(self, provider_name: str, user_id: str) -> bool:
        """Delete user via SCIM 2.0 DELETE"""
        # Implement DELETE operation
        return True

    async def scim_list_users(self, provider_name: str, filter: Optional[str] = None, start_index: int = 1, count: int = 100) -> Dict[str, Any]:
        """List users via SCIM 2.0"""
        return {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": 0,
            "itemsPerPage": count,
            "startIndex": start_index,
            "Resources": [],
        }

    async def scim_create_group(self, provider_name: str, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create group via SCIM 2.0"""
        scim_group = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": group_data.get("display_name", ""),
            "members": [{"value": m} for m in group_data.get("members", [])],
        }
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "id": f"scim_group_{secrets.token_hex(8)}",
            "displayName": group_data.get("display_name", ""),
            "meta": {
                "resourceType": "Group",
                "created": datetime.utcnow().isoformat() + "Z",
            },
        }

    # =============================================================================
    # JIT Provisioning
    # =============================================================================

    async def jit_provision_user(self, provider_name: str, user_info: Dict[str, Any]) -> User:
        """Just-in-time user provisioning from SSO"""
        user = await self._create_or_update_user(provider_name, user_info)
        return user

    async def _create_or_update_user(self, provider_name: str, user_info: Dict[str, Any]) -> User:
        external_id = user_info.get("external_id", "")
        user = self.users.get(external_id)

        if user:
            # Update existing user
            user.email = user_info.get("email", user.email)
            user.first_name = user_info.get("first_name", user.first_name)
            user.last_name = user_info.get("last_name", user.last_name)
            user.display_name = user_info.get("display_name", user.display_name)
            user.groups = user_info.get("groups", user.groups)
            user.roles = user_info.get("roles", user.roles)
            user.updated_at = datetime.utcnow()
        else:
            # Create new user
            user = User(
                id=f"user_{secrets.token_hex(8)}",
                external_id=user_info.get("external_id", secrets.token_hex(8)),
                email=user_info.get("email", ""),
                username=user_info.get("username"),
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name"),
                display_name=user_info.get("display_name"),
                groups=user_info.get("groups", []),
                roles=user_info.get("roles", []),
                provider=SSOProvider(user_info.get("provider", "saml")),
            )
            self.users[user.external_id] = user

        user.last_login = datetime.utcnow()
        user.active = True
        return user

    # =============================================================================
    # Token Management
    # =============================================================================

    def generate_saml_metadata(self, provider_name: str) -> str:
        """Generate SAML SP Metadata XML"""
        config = self.sso_configs.get(provider_name)
        if not config:
            raise ValueError(f"SSO provider {provider_name} not configured")

        base_url = self.config.get("base_url", "http://localhost:5000")

        entity_descriptor = ET.Element(
            "{urn:oasis:names:tc:SAML:2.0:metadata}EntityDescriptor",
            entityID=config.entity_id,
        )

        sso_descriptor = ET.SubElement(
            entity_descriptor,
            "{urn:oasis:names:tc:SAML:2.0:metadata}SPSSODescriptor",
            protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol",
            AuthnRequestsSigned="true",
            WantAssertionsSigned="true",
        )

        # Key descriptor (public key)
        if config.x509_cert:
            key_descriptor = ET.SubElement(key_descriptor, "KeyDescriptor", use="signing")
            key_info = ET.SubElement(key_descriptor, "{http://www.w3.org/2000/09/xmldsig#}KeyInfo")
            x509_data = ET.SubElement(key_info, "{http://www.w3.org/2000/09/xmldsig#}X509Data")
            x509_cert = ET.SubElement(x509_data, "{http://www.w3.org/2000/09/xmldsig#}X509Certificate")
            x509_cert.text = config.x509_cert

        # Assertion Consumer Service
        acs = ET.SubElement(sso_descriptor, "AssertionConsumerService")
        acs.set("Binding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST")
        acs.set("Location", f"{self.config.get('base_url', '')}/auth/saml/acs")
        acs.set("index", "0")
        acs.set("isDefault", "true")

        # Single Logout Service
        if config.slo_url:
            slo = ET.SubElement(sso_descriptor, "SingleLogoutService")
            slo.set("Binding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect")
            slo.set("Location", config.slo_url)

        # Organization info
        org = ET.SubElement(entity_descriptor, "Organization")
        org_name = ET.SubElement(org, "OrganizationName")
        org_name.text = "Git-Fix"
        org_display = ET.SubElement(org, "OrganizationDisplayName")
        org_display.text = "Git-Fix Code Review Engine"
        org_url = ET.SubElement(org, "OrganizationURL")
        org_url.text = self.config.get("base_url", "http://localhost:5000")

        # Contact person
        contact = ET.SubElement(entity_descriptor, "ContactPerson", contactType="technical")
        given_name = ET.SubElement(contact, "GivenName")
        given_name.text = "Git-Fix"
        email = ET.SubElement(contact, "EmailAddress")
        email.text = "security@gitfix.io"

        return ET.tostring(entity_descriptor, encoding="unicode", method="xml")

    def generate_jwks(self) -> Dict[str, Any]:
        """Generate JWKS for OIDC"""
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()

        # Get public key components
        numbers = public_key.public_numbers()
        n = base64.urlsafe_b64encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")).decode().rstrip("=")
        e = base64.urlsafe_b64encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")).decode().rstrip("=")

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "kid": secrets.token_hex(16),
                    "n": n,
                    "e": e,
                    "alg": "RS256",
                }
            ]
        }


class SCIMClient:
    """SCIM 2.0 Client for provisioning"""

    def __init__(self, base_url: str, bearer_token: str, version: str = "2.0"):
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.version = version
        self.client = httpx.AsyncClient(timeout=30.0)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.client.post(
            f"{self.base_url}/Users",
            json={
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                **user_data,
            },
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        response.raise_for_status()
        return response.json()

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        response = await self.client.get(
            f"{self.base_url}/Users/{user_id}",
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        response.raise_for_status()
        return response.json()

    async def update_user(self, user_id: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        response = await self.client.patch(
            f"{self.base_url}/Users/{user_id}",
            json={"schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"], "Operations": user_id},
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        response.raise_for_status()
        return response.json()

    async def delete_user(self, user_id: str) -> bool:
        response = await self.client.delete(
            f"{self.base_url}/Users/{user_id}",
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        return response.status_code == 204

    async def list_users(self, filter: Optional[str] = None, start_index: int = 1, count: int = 100) -> Dict[str, Any]:
        params = {"startIndex": start_index, "count": count}
        if filter:
            params["filter"] = filter
        response = await self.client.get(
            f"{self.base_url}/Users",
            params=params,
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        response.raise_for_status()
        return response.json()


# Factory function
def create_sso_manager(config: Dict[str, Any]) -> SSOManager:
    return SSOManager(config)


# Export
__all__ = [
    "SSOManager",
    "SSOConfig",
    "SSOProvider",
    "User",
    "Group",
    "UserStatus",
    "SCIMClient",
    "create_sso_manager",
]