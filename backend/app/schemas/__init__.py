# backend/app/schemas/__init__.py
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse
)
from app.schemas.script import (
    ScriptCreate,
    ScriptUpdate,
    ScriptResponse,
    ScriptSegment
)
from app.schemas.material import (
    MaterialCreate,
    MaterialResponse
)
from app.schemas.quality import (
    QualityReportCreate,
    QualityReportResponse
)

__all__ = [
    "ProjectCreate", "ProjectUpdate", "ProjectResponse",
    "ScriptCreate", "ScriptUpdate", "ScriptResponse", "ScriptSegment",
    "MaterialCreate", "MaterialResponse",
    "QualityReportCreate", "QualityReportResponse"
]
