from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.sync_api import sync_playwright

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

AUTH_DIR = Path("auth")
AUTH_FILE = AUTH_DIR / "ixl_state.json"
DOWNLOAD_DIR = Path("downloads")
LOG_DIR = Path("logs")

AUTH_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def safe_filename(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return text[:180] or "download"


def click_export_csv(page) -> None:
    candidates = [
        lambda: page.get_by_role("button", name=re.compile(r"export.*csv", re.I)).click(timeout=5000),
        lambda: page.get_by_text(re.compile(r"export.*csv", re.I)).click(timeout=5000),
        lambda: page.locator("text=/Export\\s*CSV/i").first.click(timeout=5000),
    ]

    last_error = None
    for action in candidates:
        try:
            action()
            return
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Could not find Export CSV button. Last error: {last_error}")


def auth_file_exists() -> bool:
    return AUTH_FILE.exists()


def run_test_one(score_url: str) -> dict[str, Any]:
    if not AUTH_FILE.exists():
        raise RuntimeError("No saved IXL auth state found. Run connect flow first.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(AUTH_FILE), accept_downloads=True)
        page = context.new_page()

        page.goto(score_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        with page.expect_download(timeout=30000) as download_info:
            click_export_csv(page)

        download = download_info.value
        filename = safe_filename(download.suggested_filename or "score_export.csv")
        out_path = DOWNLOAD_DIR / filename
        download.save_as(str(out_path))

        browser.close()

    return {
        "file_name": out_path.name,
        "file_path": str(out_path),
        "status": "exported",
    }


def fetch_assignment_rows(teacher_id: str, limit: int) -> list[dict[str, Any]]:
    supa = get_supabase()
    response = (
        supa.table("IXL_Assignments")
        .select("teacher_id, Class, Skill_Code, ScoreURL, DateAssigned")
        .eq("teacher_id", teacher_id)
        .not_.is_("ScoreURL", "null")
        .order("DateAssigned", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def run_export_sample(teacher_id: str, limit: int) -> list[dict[str, Any]]:
    if not AUTH_FILE.exists():
        raise RuntimeError("No saved IXL auth state found. Run connect flow first.")

    rows = fetch_assignment_rows(teacher_id, limit)
    exports: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(AUTH_FILE), accept_downloads=True)
        page = context.new_page()

        for row in rows:
            score_url = str(row.get("ScoreURL") or "").strip()
            skill_code = safe_filename(str(row.get("Skill_Code") or "skill"))
            class_name = safe_filename(str(row.get("Class") or "class"))
            assigned = safe_filename(str(row.get("DateAssigned") or "date"))

            if not score_url:
                continue

            page.goto(score_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)

            with page.expect_download(timeout=30000) as download_info:
                click_export_csv(page)

            download = download_info.value
            final_name = f"{teacher_id}__{class_name}__{skill_code}__{assigned}.csv"
            out_path = DOWNLOAD_DIR / safe_filename(final_name)
            download.save_as(str(out_path))

            exports.append(
                {
                    "teacher_id": teacher_id,
                    "class_name": row.get("Class"),
                    "skill_code": row.get("Skill_Code"),
                    "file_name": out_path.name,
                    "file_path": str(out_path),
                    "status": "exported",
                    "when": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        browser.close()

    return exports