$ErrorActionPreference = "Stop"

$apiBase = "http://127.0.0.1:8000/api/v1"
$tenantId = "tenant_a"
$dbPath = Join-Path (Get-Location) "demo_target.db"
$dbConn = "sqlite:///" + $dbPath

@'
from sqlalchemy import create_engine, text
engine = create_engine("sqlite:///demo_target.db")
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS users"))
    conn.execute(text("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            age INTEGER,
            department TEXT,
            first_name TEXT,
            last_name TEXT
        )
    """))
print("OK")
'@ | python -

$csvPath = Join-Path (Get-Location) "tmp_sample_users.csv"
@"
Email Address,Age,Department,Full Name
alice@example.com,29,Engineering,Alice Smith
bad-email,22,Sales,Jane Doe
"@ | Set-Content -Path $csvPath -NoNewline

$jobJson = @"
import json
import mimetypes
import pathlib
import urllib.request
import uuid

api_base = "http://127.0.0.1:8000/api/v1"
tenant_id = "tenant_a"
db_connection = r"$dbConn"
file_path = pathlib.Path(r"$csvPath")
boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

parts = []
for name, value in [("tenant_id", tenant_id), ("db_connection", db_connection)]:
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
    parts.append(f"{value}\r\n".encode())

content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
parts.append(f"--{boundary}\r\n".encode())
parts.append(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode())
parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
parts.append(file_path.read_bytes())
parts.append(b"\r\n")
parts.append(f"--{boundary}--\r\n".encode())

body = b"".join(parts)
request = urllib.request.Request(
    f"{api_base}/imports/upload",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
with urllib.request.urlopen(request) as response:
    print(response.read().decode("utf-8"))
"@ | python -

$job = $jobJson | ConvertFrom-Json
Write-Host "Job ID: $($job.job_id)"

Start-Sleep -Seconds 2
$status = Invoke-RestMethod -Method Get -Uri "$apiBase/import/status/$($job.job_id)"
$status | ConvertTo-Json -Depth 10

Write-Host "If the file has invalid rows, use the UI to download the error workbook, fix the Error-marked rows, and re-upload it."
