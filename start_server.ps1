$ENV_DIR = "C:\Users\KESHAV\Documents\bookourshow\.venv"
$SERVER_SCRIPT = '
import uvicorn
from app.main import app

uvicorn.run(app, host="127.0.0.1", port=8000)
'

$SERVER_PATH = "$ENV_DIR\Scripts\python.exe"
$output_file = "server.log"

Write-Host "Starting server..." -ForegroundColor Cyan
& $SERVER_SCRIPT $SERVER_PATH --host 127.0.0.1 --port 8000 &

# Wait for server to start
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = [uri]::Http "(GET,http://127.0.0.1:8000/shows/1/seats)" | Invoke-WebRequest -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "Server started successfully!" -ForegroundColor Green
            $result = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/shows/1/seats' -Method Get
            Write-Host "`nAPI Response:" -ForegroundColor Yellow
            $json = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/shows/1/seats' -Method Get | ConvertTo-Json -Depth 5
            Write-Host $json -ForegroundColor Cyan
        }
    } catch {
        Write-Host "Still waiting for server... ($i/30)" -ForegroundColor Yellow
        Start-Sleep -Seconds 1
    }
}
