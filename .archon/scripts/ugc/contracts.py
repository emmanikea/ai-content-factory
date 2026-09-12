#!/usr/bin/env python3
"""Provider-neutral contracts for UGC Studio.

No paid APIs are called from this module. It is intentionally standard-library only so
planning and validation can run anywhere the current factory runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RightsMode(str, Enum):
    CREATIVE_DNA_ONLY = "creative_dna_only"
    LICENSED_PERFORMANCE_TRANSFER = "licensed_performance_transfer"
    OWNED_SOURCE = "owned_source"


class SourceType(str, Enum):
    CREATOR_GENERATED = "creator_generated"
    CREATOR_MOTION_TRANSFER = "creator_motion_transfer"
    CREATOR_LIPSYNC = "creator_lipsync"
    APP_CAPTURE = "app_capture"
    PRODUCT_CAPTURE = "product_capture"
    BROLL_GENERATED = "broll_generated"
    OWNED_MEDIA = "owned_media"
    GRAPHIC = "graphic"


class Capability(str, Enum):
    IDENTITY_STILL = "identity_still"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    REFERENCE_TO_VIDEO = "reference_to_video"
    MOTION_TRANSFER = "motion_transfer"
    CHARACTER_REPLACE = "character_replace"
    VIDEO_EDIT = "video_edit"
    VOICE_CLONE = "voice_clone"
    SPEECH = "speech"
    LIP_SYNC = "lip_sync"
    BROLL = "broll"
    APP_CAPTURE = "app_capture"


@dataclass(frozen=True)
class ShotSpec:
    id: str
    start: float
    end: float
    source_type: SourceType
    purpose: str
    dialogue: str | None = None
    visual_direction: str | None = None
    capture_script: str | None = None
    motion_reference_id: str | None = None
    required_capabilities: tuple[Capability, ...] = ()
    provider_preference: str | None = None
    provider_fallback: str | None = None

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


@dataclass(frozen=True)
class CreativeSpec:
    version: str
    campaign_id: str
    concept_id: str
    format: str
    duration_seconds: float
    aspect_ratio: str
    hook: str
    angle: str
    creator_id: str
    rights_mode: RightsMode
    shots: tuple[ShotSpec, ...]
    script: str = ""
    language: str = "en"
    cta: str = ""
    quality_tier: str = "standard"
    max_render_cost_usd: float | None = None


@dataclass(frozen=True)
class ProviderQuote:
    provider: str
    model: str
    capability: Capability
    estimated_cost_usd: float
    quality_score: float
    latency_score: float = 0.5
    qa_pass_rate: float = 0.8
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderPlanItem:
    shot_id: str
    source_type: SourceType
    action: str
    provider: str
    model: str
    estimated_cost_usd: float
    reason: str


@dataclass(frozen=True)
class RenderPlan:
    concept_id: str
    items: tuple[RenderPlanItem, ...]
    estimated_total_usd: float
    blocked: bool = False
    block_reason: str | None = None
