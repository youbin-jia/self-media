# backend/app/api/llm.py
from fastapi import APIRouter
from app.services.llm import llm_manager

router = APIRouter()


@router.get("/providers")
async def list_providers():
    """列出所有可用的LLM Provider"""
    return llm_manager.list_providers()


@router.post("/set-default/{provider_name}")
async def set_default_provider(provider_name: str):
    """设置默认LLM Provider"""
    try:
        provider = llm_manager.get_provider(provider_name)
        # 更新配置或会话状态
        return {
            "status": "success",
            "message": f"默认Provider已切换到{provider_name}",
            "provider": {
                "name": provider.provider_name,
                "models": provider.available_models
            }
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}
