# Server Start Script
$env:PYTHONPATH = "C:\Users\KESHAV\Documents\bookourshow\.venv"
$output_file = "server_output.txt"

Write-Host "Starting uvicorn server in background..." -ForegroundColor Cyan

Start-Process python -ArgumentList "C:\Users\KESHAV\Documents\bookourshow\.venv\Scripts\python.exe", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "4" -WorkingDirectory "C:\Users\KESHAV\Documents\bookourshow\backend" -RedirectStandardOutput $output_file -PassThru

Write-Host "Server started. Waiting for startup..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Test API
Write-Host "`nTesting API: GET /shows/1/seats" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/shows/1/seats' -TimeoutSec 30
    Write-Host "`nStatus Code: $($response.StatusCode)" -ForegroundColor Green
    
    if ($response.StatusCode -eq 200) {
        $json = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/shows/1/seats' -TimeoutSec 30 | ConvertTo-Json -Depth 5
        Write-Host "`nResponse JSON:" -ForegroundColor Cyan
        Write-Host $json
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Get-Content $output_file -Raw | Set-Content $output_file
    Write-Host "Server logs:" -ForegroundColor Yellow
    Get-Content $output_file
}
