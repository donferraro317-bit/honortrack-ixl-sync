from fastapi import Request
import secrets

CONNECT_SESSIONS = {}

@app.post("/api/ixl/connect")
def connect_ixl():
    token = secrets.token_urlsafe(16)

    CONNECT_SESSIONS[token] = {
        "status": "pending"
    }

    login_url = f"/ixl-connect/{token}"

    return {
        "message": "Open this link to connect IXL",
        "login_url": login_url
    }

from fastapi.responses import HTMLResponse

@app.get("/ixl-connect/{token}", response_class=HTMLResponse)
def ixl_connect_page(token: str):

    if token not in CONNECT_SESSIONS:
        return "<h1>Invalid session</h1>"

    return f"""
    <html>
    <body style="font-family:sans-serif;background:#0b1020;color:white;text-align:center;padding-top:80px;">
        <h1>Connect IXL</h1>
        <p>Click below to log into IXL</p>

        <a href="/ixl-connect-start/{token}" 
           style="padding:12px 20px;background:#2e6cff;color:white;text-decoration:none;border-radius:8px;">
           Login to IXL
        </a>
    </body>
    </html>
    """

from threading import Thread
from playwright.sync_api import sync_playwright


@app.get("/ixl-connect-start/{token}")
def start_ixl_login(token: str):

    def run():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()

            page = context.new_page()
            page.goto("https://www.ixl.com/signin")

            # wait for user to login manually
            page.wait_for_timeout(60000)

            context.storage_state(path="auth/ixl_state.json")

            browser.close()

            CONNECT_SESSIONS[token]["status"] = "connected"

    Thread(target=run).start()

    return {"message": "Login window started. Complete login within 60 seconds."}
