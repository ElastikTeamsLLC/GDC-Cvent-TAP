"""Stream type classes for tap-cvent."""

from __future__ import annotations

import typing as t
from importlib import resources

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_cvent.client import CventStream


SCHEMAS_DIR = resources.files(__package__) / "schemas"


class AdmissionItemsStream(CventStream):
    """Stream for Cvent Admission Items API."""

    name = "admission_items"
    path = "admission-items"
    primary_keys: t.ClassVar[list[str]] = ["id"]
    replication_key = "lastModified"
    
    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("name", th.StringType),
        th.Property("code", th.StringType),
        th.Property("lastModified", th.DateTimeType),
        th.Property("created", th.DateTimeType),
        th.Property("allowOptionalSessions", th.BooleanType),
        th.Property(
            "limitedAvailableSessions", 
            th.ArrayType(th.StringType),
            description="List of limited available sessions"
        ),
        th.Property(
            "event", 
            th.ObjectType(
                th.Property("id", th.StringType),
                th.Property("languages", th.ArrayType(th.StringType))
            ),
            description="Event details"
        ),
        th.Property(
            "includedSessions", 
            th.ArrayType(th.StringType),
            description="List of included sessions"
        ),
    ).to_dict()