"""
Google Drive API v3 Report Storage & Cloud Archiving Service (Section 2 & Section 9).
Archives generated Friday PDF reports and Excel data workbooks to a configured Google Drive folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("fmip.reporting.drive")


class GoogleDriveArchiver:
    """Uploads PDF and Excel reports to Google Drive using a GCP Service Account."""

    @staticmethod
    def is_configured() -> bool:
        cred_path = Path(settings.GOOGLE_APPLICATION_CREDENTIALS)
        return bool(
            settings.GOOGLE_DRIVE_ENABLED
            and cred_path.exists()
            and settings.GOOGLE_DRIVE_REPORTS_FOLDER_ID
        )

    @classmethod
    def upload_file_to_drive(
        cls,
        file_path: str | Path,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upload `file_path` to Google Drive and return the created Drive `file_id`,
        or `None` if credentials are not configured yet.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Cannot archive missing file to Google Drive: {path}")

        if not cls.is_configured():
            logger.info(
                "Google Drive archiving skipped (awaiting GOOGLE_APPLICATION_CREDENTIALS / GOOGLE_DRIVE_ENABLED=true in .env)."
            )
            return None

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            scopes = ["https://www.googleapis.com/auth/drive.file"]
            creds = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS,
                scopes=scopes,
            )
            service = build("drive", "v3", credentials=creds, cache_discovery=False)
            target_folder = folder_id or settings.GOOGLE_DRIVE_REPORTS_FOLDER_ID
            file_metadata: Dict[str, Any] = {"name": path.name}
            if target_folder:
                file_metadata["parents"] = [target_folder]

            media = MediaFileUpload(str(path), mimetype=mime_type, resumable=False)
            created = (
                service.files()
                .create(body=file_metadata, media_body=media, fields="id, webViewLink")
                .execute()
            )
            file_id = str(created.get("id", ""))
            logger.info("Archived %s to Google Drive (file_id=%s)", path.name, file_id)
            return file_id
        except Exception as exc:
            logger.warning("Google Drive upload error for %s: %s", path.name, exc)
            return None
