# backend/app/api/quality.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.quality_detector import QualityDetector
from app.schemas.quality import ComprehensiveQualityReport

router = APIRouter()


@router.get("/detect/{project_id}", response_model=ComprehensiveQualityReport)
async def detect_project_quality(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    检测项目综合质量
    Args:
        project_id: 项目ID
        db: 数据库会话
    Returns:
        综合质量报告
    """
    try:
        detector = QualityDetector()
        report = await detector.detect_comprehensive_quality(project_id, db)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality detection failed: {str(e)}")
