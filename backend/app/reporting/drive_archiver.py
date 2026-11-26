"""
Google Drive API v3 Report Storage & Cloud Archiving Service (Section 2 & Section 9).
Supports:
1. Keyless Google Cloud Organization Policy Authentication (`iam.disableServiceAccountKeyCreation` compliant):
   - Uses existing `gcloud auth application-default login` (`cloud-platform` scope, which is NEVER blocked by Google OAuth!)
   - Impersonates `GOOGLE_DRIVE_SERVICE_ACCOUNT_EMAIL` (`fmip-drive-archiver@project-78a44216-78a2-43e0-a7e.iam.gserviceaccount.com`)
     via IAM Credentials REST API (`iamcredentials.googleapis.com`) using SSL-resilient `create_http_client()`
   - Uploads files directly to Google Drive API v3 (`www.googleapis.com/upload/drive/v3/files`)
2. Standard Service Account JSON Key File (`GOOGLE_APPLICATION_CREDENTIALS`) when present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import uuid

from app.core.config import settings
from app.core.logging import get_logger
from app.core.ssl_helper import create_google_auth_request, create_http_client

logger = get_logger("fmip.reporting.drive")

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
CLOUD_PLATFORM_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class GoogleDriveArchiver:
    """Uploads PDF and Excel reports to Google Drive using Keyless Service Account Impersonation or JSON key."""

    @staticmethod
    def _obtain_drive_access_token() -> Optional[str]:
        """
        Obtain a valid OAuth2 Bearer token with Google Drive scope:
        1. If a Service Account JSON file exists at `GOOGLE_APPLICATION_CREDENTIALS`, refresh it via `create_google_auth_request()`.
        2. Otherwise, load `google.auth.default()` (existing `gcloud` ADC credentials), refresh the `cloud-platform`
           token via `create_google_auth_request()`, and exchange it for a short-lived Drive token for
           `GOOGLE_DRIVE_SERVICE_ACCOUNT_EMAIL` via `iamcredentials.googleapis.com`.
        """
        auth_req = create_google_auth_request()
        cred_path = Path(settings.GOOGLE_APPLICATION_CREDENTIALS)
        if cred_path.exists() and cred_path.is_file():
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_file(
                str(cred_path),
                scopes=DRIVE_SCOPES,
            )
            creds.refresh(auth_req)
            return str(creds.token)

        import google.auth

        source_creds, project_id = google.auth.default(scopes=CLOUD_PLATFORM_SCOPES)
        source_creds.refresh(auth_req)
        source_token = str(source_creds.token)

        sa_email = settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_EMAIL.strip()
        quota_project = project_id or "project-78a44216-78a2-43e0-a7e"
        if "@" in sa_email and ".iam.gserviceaccount.com" in sa_email:
            quota_project = sa_email.split("@")[1].split(".iam.gserviceaccount.com")[0]

        if sa_email:
            iam_url = (
                f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
                f"{sa_email}:generateAccessToken"
            )
            headers = {
                "Authorization": f"Bearer {source_token}",
                "x-goog-user-project": quota_project,
                "Content-Type": "application/json",
            }
            with create_http_client(timeout=20) as client:
                resp = client.post(
                    iam_url,
                    headers=headers,
                    json={"scope": DRIVE_SCOPES, "lifetime": "3600s"},
                )
                if resp.status_code == 200:
                    return str(resp.json().get("accessToken", ""))
                logger.info(
                    "Service Account impersonation response (%s): %s. "
                    "Grant Token Creator role via: gcloud iam service-accounts add-iam-policy-binding %s "
                    "--member=user:%s --role=roles/iam.serviceAccountTokenCreator --project=%s",
                    resp.status_code,
                    resp.text[:250],
                    sa_email,
                    settings.SMTP_USERNAME,
                    quota_project,
                )

        return source_token

    @staticmethod
    def is_configured() -> bool:
        return bool(
            settings.GOOGLE_DRIVE_ENABLED and settings.GOOGLE_DRIVE_REPORTS_FOLDER_ID
        )

    @classmethod
    def upload_file_to_drive(
        cls,
        file_path: str | Path,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upload `file_path` to Google Drive folder `GOOGLE_DRIVE_REPORTS_FOLDER_ID`
        (`1cCL2koCp9Qvjaq95T2pZP3sRPpCU2c5K`) via direct multipart REST call and return `file_id`.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Cannot archive missing file to Google Drive: {path}")

        if not cls.is_configured():
            logger.info("Google Drive archiving skipped (GOOGLE_DRIVE_ENABLED is false).")
            return None

        try:
            access_token = cls._obtain_drive_access_token()
            if not access_token:
                return None

            target_folder = (folder_id or settings.GOOGLE_DRIVE_REPORTS_FOLDER_ID).strip()
            metadata = {"name": path.name}
            if target_folder:
                metadata["parents"] = [target_folder]  # type: ignore[assignment]

            boundary = f"fmip_boundary_{uuid.uuid4().hex}"
            meta_json = json.dumps(metadata).encode("utf-8")
            file_bytes = path.read_bytes()

            body = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            ).encode("utf-8") + meta_json + (
                f"\r\n--{boundary}\r\n"
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

            upload_url = (
                "https://www.googleapis.com/upload/drive/v3/files"
                "?uploadType=multipart&supportsAllDrives=true&fields=id,webViewLink"
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            }

            with create_http_client(timeout=30) as client:
                resp = client.post(upload_url, headers=headers, content=body)
                if resp.status_code in (200, 201):
                    file_id = str(resp.json().get("id", ""))
                    logger.info("Archived %s to Google Drive (file_id=%s)", path.name, file_id)
                    return file_id
                logger.info(
                    "Google Drive API status %s for %s: %s",
                    resp.status_code,
                    path.name,
                    resp.text[:250],
                )
                return None
        except Exception as exc:
            logger.info("Google Drive archiving note for %s: %s", path.name, exc)
            return None
