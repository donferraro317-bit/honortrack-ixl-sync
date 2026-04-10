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
