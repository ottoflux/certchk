from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import ssl
import socket
import datetime
import asyncio
import concurrent.futures

app = FastAPI(title="SSL Cert Checker")

# --- Data Models ---
class DomainRequest(BaseModel):
    domains: List[str]

class CertInfo(BaseModel):
    server: str
    status: str  # "ok" or "error"
    expiry_date: Optional[str] = None
    days_left: Optional[int] = None
    error_message: Optional[str] = None

# --- Core Logic ---
def get_cert_details(server: str) -> CertInfo:
    """
    Synchronous blocking function to check SSL.
    """
    # Clean up domain input
    clean_server = server.replace("https://", "").replace("http://", "").split("/")[0]

    context = ssl.create_default_context()

    try:
        # 3.0s timeout is critical for serverless functions to not time out entirely
        with socket.create_connection((clean_server, 443), timeout=3.0) as sock:
            with context.wrap_socket(sock, server_hostname=clean_server) as ssock:
                cert = ssock.getpeercert()

                if cert:
                    expiry_date = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                    days_left = (expiry_date - datetime.datetime.now()).days

                    return CertInfo(
                        server=clean_server,
                        status="ok",
                        expiry_date=expiry_date.strftime("%Y-%m-%d"),
                        days_left=days_left
                    )
                else:
                    return CertInfo(
                        server=clean_server,
                        status="error",
                        error_message="Certificate not available"
                    )

    except socket.timeout:
         return CertInfo(server=clean_server, status="error", error_message="Connection timed out")
    except socket.gaierror:
         return CertInfo(server=clean_server, status="error", error_message="DNS lookup failed")
    except ssl.SSLError as e:
         return CertInfo(server=clean_server, status="error", error_message=f"SSL Error: {str(e)}")
    except Exception as e:
        return CertInfo(server=clean_server, status="error", error_message=str(e))

# --- API Endpoints ---

@app.get("/")
def home():
    return {"message": "SSL Checker API is ready. POST to /check"}

@app.post("/check", response_model=List[CertInfo])
async def check_domains(request: DomainRequest):
    loop = asyncio.get_running_loop()

    # Vercel Free Tier has a 10-second timeout limit.
    # We use threading to check all domains at once so we fit in that window.
    with concurrent.futures.ThreadPoolExecutor() as pool:
        tasks = []
        for domain in request.domains:
            if domain.strip():
                tasks.append(
                    loop.run_in_executor(pool, get_cert_details, domain.strip())
                )

        results = await asyncio.gather(*tasks)

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
