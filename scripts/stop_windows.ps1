$ErrorActionPreference = "Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path)
Set-Location ..
docker compose down
Write-Host "App stopped"
