"""
Institutional PDF Research Report Parser & Intelligence Extractor.
Reads financial PDF documents (CBN MPC Communiques, NBS CPI/GDP releases, DMO Debt Reports,
IMF WEO, Asset Management Weekly Market Reports), extracts structured text, numerical tables,
and key market figures, sanitizes against indirect prompt injection, and persists searchable
768-dim vector chunks into FMIP's institutional research memory.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import PromptInjectionSanitizer
from app.models.document import DocumentChunk, ResearchDocument
from app.services.ingestion_service import IngestionService, compute_text_embedding_768

logger = get_logger("fmip.services.pdf_parser")


class InstitutionalPDFResearchParser:
    """Extracts structured text, key financial metrics, and vector chunks from PDF reports."""

    METRIC_PATTERNS: List[tuple[str, re.Pattern[str]]] = [
        ("mpr_mentions", re.compile(r"(?:Monetary Policy Rate|MPR)[^0-9]{0,25}(\d{1,2}\.\d{1,2})\s*%", re.I)),
        ("cpi_mentions", re.compile(r"(?:Headline Inflation|CPI)[^0-9]{0,25}(\d{1,2}\.\d{1,2})\s*%", re.I)),
        ("pmi_mentions", re.compile(r"(?:Composite PMI|Manufacturing PMI|CBN PMI|S&P Global PMI)[^0-9]{0,25}(\d{2}\.\d)", re.I)),
        ("fx_usdngn_mentions", re.compile(r"(?:USD/?NGN|NAFEM|NFEM)[^0-9]{0,25}[N₦]?\s*(\d{1},?\d{3}(?:\.\d{1,2})?)", re.I)),
        ("reserves_mentions", re.compile(r"(?:External Reserves|Foreign Reserves)[^0-9]{0,25}\$?\s*(\d{2}\.\d{1,2})\s*(?:billion|bn|B)", re.I)),
        ("brent_mentions", re.compile(r"(?:Brent\s+crude|Brent)[^0-9]{0,25}\$?\s*(\d{2,3}\.\d{1,2})", re.I)),
        ("us10y_mentions", re.compile(r"(?:US\s*10-?year|10-?year\s+Treasury)[^0-9]{0,25}(\d\.\d{1,2})\s*%", re.I)),
    ]

    @classmethod
    def extract_from_bytes(cls, pdf_bytes: bytes, filename: str = "uploaded_report.pdf") -> Dict[str, Any]:
        """Extract per-page text, table-like numerical lines, and financial indicators from raw PDF bytes."""
        pages_text: List[Dict[str, Any]] = []
        parser_engine = "pypdf"

        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(pdf_bytes))
            for idx, page in enumerate(reader.pages, start=1):
                raw_txt = page.extract_text() or ""
                sanitized = PromptInjectionSanitizer.sanitize(
                    raw_txt, source_id="PDF_RESEARCH_PARSER", source_url=filename
                )
                pages_text.append(
                    {
                        "page_number": idx,
                        "char_count": len(sanitized.clean_text),
                        "text": sanitized.clean_text,
                        "injection_blocked": sanitized.injection_detected,
                    }
                )
        except Exception as exc:
            parser_engine = f"fallback_ascii ({exc})"
            raw_ascii = re.findall(rb"[A-Za-z0-9\s\.\,\-\%\$\(\)\/\:]{12,}", pdf_bytes)
            joined = "\n".join(b.decode("ascii", errors="ignore") for b in raw_ascii[:400])
            sanitized = PromptInjectionSanitizer.sanitize(
                joined, source_id="PDF_RESEARCH_PARSER", source_url=filename
            )
            pages_text.append(
                {
                    "page_number": 1,
                    "char_count": len(sanitized.clean_text),
                    "text": sanitized.clean_text,
                    "injection_blocked": sanitized.injection_detected,
                }
            )

        full_text = "\n\n".join(p["text"] for p in pages_text if p["text"])
        extracted_metrics: Dict[str, List[str]] = {}
        for label, pat in cls.METRIC_PATTERNS:
            hits = pat.findall(full_text)
            if hits:
                extracted_metrics[label] = list(dict.fromkeys(hits))[:8]

        # Extract numerical table-like lines (lines containing >= 2 numeric figures or percentages)
        table_lines: List[str] = []
        for line in full_text.splitlines():
            clean_ln = " ".join(line.split())
            if len(clean_ln) < 12 or len(clean_ln) > 180:
                continue
            nums = re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?%?", clean_ln)
            if len(nums) >= 2:
                table_lines.append(clean_ln)

        return {
            "filename": filename,
            "parser_engine": parser_engine,
            "page_count": len(pages_text),
            "total_characters": len(full_text),
            "pages": pages_text,
            "extracted_financial_metrics": extracted_metrics,
            "numerical_table_rows_sample": table_lines[:40],
            "full_text": full_text,
            "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        }

    @classmethod
    def ingest_pdf_into_research_memory(
        cls,
        db: Session,
        pdf_bytes: bytes,
        filename: str,
        title: Optional[str] = None,
        source_code: str = "CBN_OFFICIAL",
        document_type: str = "INSTITUTIONAL_RESEARCH_PDF",
    ) -> Dict[str, Any]:
        """Parse a PDF report, persist it as a ResearchDocument, and embed its pages into DocumentChunk."""
        parsed = cls.extract_from_bytes(pdf_bytes, filename=filename)
        sources_map = IngestionService.ensure_default_data_sources(db)
        ds = sources_map.get(source_code) or next(iter(sources_map.values()))

        content_hash = parsed["sha256"]
        existing = db.execute(
            select(ResearchDocument).where(ResearchDocument.content_hash == content_hash)
        ).scalar_one_or_none()
        if existing:
            return {
                "status": "ALREADY_INGESTED",
                "document_id": existing.id,
                "title": existing.title,
                "page_count": parsed["page_count"],
                "extracted_financial_metrics": parsed["extracted_financial_metrics"],
                "chunks_indexed": 0,
            }

        from app.models.source import SourceRegister

        sr = SourceRegister(
            source_id=ds.id,
            source_name=ds.name,
            publication_title=title or Path(filename).stem.replace("_", " ").replace("-", " ").title(),
            publication_date=datetime.now(timezone.utc),
            url=f"local://ingested-pdfs/{filename}",
            canonical_hash=content_hash,
            relevant_finding=(
                f"Ingested {parsed['page_count']}-page institutional PDF ({filename}). "
                f"Extracted metric categories: {', '.join(parsed['extracted_financial_metrics'].keys()) or 'general commentary'}."
            ),
            reliability_classification=ds.reliability_tier or "TIER_2_INSTITUTIONAL",
            epistemic_type="FACT",
            verification_status="VERIFIED",
        )
        db.add(sr)
        db.flush()

        doc = ResearchDocument(
            source_register_id=sr.id,
            document_type=document_type,
            title=sr.publication_title,
            issuer=ds.name,
            published_at=datetime.now(timezone.utc),
            raw_text=parsed["full_text"][:50000],
            structured_extract={
                "parser_engine": parsed["parser_engine"],
                "page_count": parsed["page_count"],
                "extracted_financial_metrics": parsed["extracted_financial_metrics"],
                "table_rows_detected": len(parsed["numerical_table_rows_sample"]),
            },
            content_hash=content_hash,
        )
        db.add(doc)
        db.flush()

        chunks_created = 0
        for page in parsed["pages"]:
            txt = page["text"].strip()
            if len(txt) < 20:
                continue
            c_txt = txt[:2800]
            emb = compute_text_embedding_768(c_txt)
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=page["page_number"],
                    chunk_text=c_txt,
                    embedding=emb,
                    metadata_json={
                        "filename": filename,
                        "page_number": page["page_number"],
                        "token_count": len(c_txt.split()),
                    },
                )
            )
            chunks_created += 1

        db.commit()
        logger.info(
            "Ingested PDF '%s' (%d pages, %d vector chunks) into institutional research memory.",
            filename,
            parsed["page_count"],
            chunks_created,
        )
        return {
            "status": "INGESTED",
            "document_id": doc.id,
            "source_register_id": sr.id,
            "title": doc.title,
            "page_count": parsed["page_count"],
            "chunks_indexed": chunks_created,
            "extracted_financial_metrics": parsed["extracted_financial_metrics"],
            "numerical_table_rows_detected": len(parsed["numerical_table_rows_sample"]),
        }
