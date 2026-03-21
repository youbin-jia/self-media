# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a self-media video automation platform (自媒体视频自动化平台) that automates the entire video production pipeline from topic discovery to video export.

## Development Commands

### Backend

```bash
# Create and activate conda environment
conda env create -f environment.yml
conda activate self-media

# Update environment (after dependency changes)
conda env update -f environment.yml --prune

# Run development server
cd backend && uvicorn app.main:app --reload

# Run Celery worker (for async tasks)
cd backend && celery -A app.tasks.celery_app worker --loglevel=info -Q high,medium,low

# Run tests
cd backend && pytest tests/ -v

# Run single test file
cd backend && pytest tests/test_auth.py -v

# Run single test
cd backend && pytest tests/test_auth.py::test_login -v
```

### Frontend

```bash
# Install dependencies
cd frontend && npm install

# Run development server
cd frontend && npm run dev

# Build for production
cd frontend && npm run build
```

### Code Quality

```bash
# Format code
black backend/app/

# Type check
mypy backend/app/

# Lint
ruff check backend/app/
```

## Architecture

### Backend Structure

```
backend/app/
├── api/           # FastAPI route handlers
├── models/        # SQLAlchemy ORM models
├── schemas/       # Pydantic validation models
├── services/      # Business logic layer
│   ├── llm/       # LLM providers (Claude, OpenAI, GLM)
│   ├── tts/       # TTS providers (Azure, ElevenLabs)
│   ├── ai_generation/  # Image generation (DALL-E)
│   ├── cache/     # Redis caching
│   └── ...
├── middleware/    # Auth, RBAC middleware
├── tasks/         # Celery async tasks
└── config.py      # Pydantic settings
```

### Key Patterns

**Provider Pattern**: LLM and TTS services use abstract base classes (`BaseLLMProvider`, `BaseTTSProvider`) allowing easy provider switching. Check `backend/app/services/llm/base.py` and `backend/app/services/tts/base.py`.

**Video Generation Pipeline**: Topic → Script → Materials → Video Synthesis → Export

**Plugin System**: Extensible material sources via plugins in `plugins/material_sources/`. Inherit from `MaterialSourcePlugin` base class.

### Configuration

All configuration via environment variables in `backend/.env`. Key settings:
- `JWT_SECRET_KEY`: Required in production
- `DEFAULT_LLM_PROVIDER`: claude | openai | glm
- `DEFAULT_TTS_PROVIDER`: azure | elevenlabs
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`: LLM API keys
- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`: TTS config

### Authentication

JWT-based auth with RBAC (admin/editor/viewer roles). Auth middleware at `backend/app/middleware/auth.py`. Projects are isolated by `owner_id` and `team_members`.

### Task Queues

Celery with three priority queues:
- `high`: Real-time tasks (video generation)
- `medium`: Batch operations
- `low`: Cleanup tasks

### Caching

Redis caching with TTLs defined in `config.py`. Use `@cache_result` and `@invalidate_cache` decorators from `app.services.cache.redis_cache`.
