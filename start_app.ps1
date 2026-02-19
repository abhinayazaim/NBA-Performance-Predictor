# Start Backend and Frontend concurrently

$backendProcess = Start-Process -FilePath "uvicorn" -ArgumentList "main:app --reload --port 8008" -WorkingDirectory "backend" -PassThru -NoNewWindow
Write-Host "starting backend..."

# Wait a moment for backend to init
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "starting frontend..."
Set-Location "frontend"
npm run dev

# Cleanup on exit (Ctrl+C)
Stop-Process -Id $backendProcess.Id -Force
