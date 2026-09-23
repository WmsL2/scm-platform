from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base
from app.common.uuid_type import UUIDChar36


class RecommendationTemplateMapping(Base):
    __tablename__ = "scm_recommendation_template_mapping"
    __table_args__ = (
        Index("ix_scm_recommendation_template_mapping_project_id", "project_id"),
        Index("ix_scm_recommendation_template_mapping_template_file_id", "template_file_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    template_file_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    template_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    header_row: Mapped[int] = mapped_column(Integer, nullable=False)
    data_start_row: Mapped[int] = mapped_column(Integer, nullable=False)
    mapping_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
