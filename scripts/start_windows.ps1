$ErrorActionPreference = "Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path)
Set-Location ..
docker compose up --build -d
Write-Host "App running at http://localhost:8000"
