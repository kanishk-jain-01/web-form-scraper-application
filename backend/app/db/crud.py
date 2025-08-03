from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from .models import Website, FormField, ScrapeJob
import logging

logger = logging.getLogger(__name__)


class WebsiteCRUD:
    @staticmethod
    async def create_website(
        db: AsyncSession,
        name: str,
        base_url: str,
        login_required: bool = False,
        login_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Website:
        website = Website(
            name=name,
            base_url=base_url,
            login_required=login_required,
            login_url=login_url,
            metadata_json=metadata or {}
        )
        db.add(website)
        await db.commit()
        await db.refresh(website)
        return website

    @staticmethod
    async def get_website_by_url(db: AsyncSession, base_url: str) -> Optional[Website]:
        result = await db.execute(
            select(Website).where(Website.base_url == base_url)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_website_with_fields(db: AsyncSession, website_id: int) -> Optional[Website]:
        result = await db.execute(
            select(Website)
            .options(selectinload(Website.form_fields))
            .where(Website.id == website_id)
        )
        return result.scalar_one_or_none()


class FormFieldCRUD:
    @staticmethod
    async def create_form_field(
        db: AsyncSession,
        website_id: int,
        field_name: str,
        field_type: str,
        selector: str,
        required: bool = False,
        max_length: Optional[int] = None,
        options: Optional[List] = None,
        validation_rules: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> FormField:
        form_field = FormField(
            website_id=website_id,
            field_name=field_name,
            field_type=field_type,
            selector=selector,
            required=required,
            max_length=max_length,
            options=options or [],
            validation_rules=validation_rules or {},
            metadata_json=metadata or {}
        )
        db.add(form_field)
        await db.commit()
        await db.refresh(form_field)
        return form_field

    @staticmethod
    async def get_fields_by_website(db: AsyncSession, website_id: int) -> List[FormField]:
        result = await db.execute(
            select(FormField).where(FormField.website_id == website_id)
        )
        return result.scalars().all()


class ScrapeJobCRUD:
    @staticmethod
    async def create_scrape_job(
        db: AsyncSession,
        website_id: int,
        job_id: str,
        target_url: str,
        status: str = "pending"
    ) -> ScrapeJob:
        scrape_job = ScrapeJob(
            website_id=website_id,
            job_id=job_id,
            target_url=target_url,
            status=status
        )
        db.add(scrape_job)
        await db.commit()
        await db.refresh(scrape_job)
        return scrape_job

    @staticmethod
    async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[ScrapeJob]:
        result = await db.execute(
            select(ScrapeJob).where(ScrapeJob.job_id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_job_status(
        db: AsyncSession,
        job_id: str,
        status: str,
        current_action: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        form_data: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> Optional[ScrapeJob]:
        result = await db.execute(
            select(ScrapeJob).where(ScrapeJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if job:
            job.status = status
            if current_action is not None:
                job.current_action = current_action
            if progress_percentage is not None:
                job.progress_percentage = progress_percentage
            if form_data is not None:
                job.form_data = form_data
            if error_message is not None:
                job.error_message = error_message
            
            await db.commit()
            await db.refresh(job)
        
        return job

    @staticmethod
    async def set_human_input_required(
        db: AsyncSession,
        job_id: str,
        required: bool,
        prompt: Optional[str] = None
    ) -> Optional[ScrapeJob]:
        result = await db.execute(
            select(ScrapeJob).where(ScrapeJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if job:
            job.requires_human_input = required
            job.human_input_prompt = prompt
            await db.commit()
            await db.refresh(job)
        
        return job

    @staticmethod
    async def get_active_jobs(db: AsyncSession) -> List[ScrapeJob]:
        result = await db.execute(
            select(ScrapeJob)
            .where(ScrapeJob.status.in_(["pending", "running"]))
            .order_by(ScrapeJob.created_at.desc())
        )
        return result.scalars().all()
