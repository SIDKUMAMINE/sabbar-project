"""Endpoints API"""
from app.api.v1.endpoints import properties
from app.api.v1.endpoints import ai
from app.api.v1.endpoints import leads
from app.api.v1.endpoints import conversations

__all__ = ["properties", "ai", "leads", "conversations"]