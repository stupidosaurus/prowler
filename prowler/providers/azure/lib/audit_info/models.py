from dataclasses import dataclass
from typing import Any, Optional

from azure.identity import DefaultAzureCredential
from pydantic import BaseModel


class Azure_Identity_Info(BaseModel):
    identity_id: str = None
    identity_type: str = None
    tenant_ids: list[str] = []
    domain: str = None
    subscriptions: dict = {}


@dataclass
class Azure_Audit_Info:
    credentials: DefaultAzureCredential
    identity: Azure_Identity_Info
    audit_metadata: Optional[Any]

    def __init__(self, credentials, identity, audit_metadata):
        self.credentials = credentials
        self.identity = identity
        self.audit_metadata = audit_metadata
