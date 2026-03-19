# Test-Script für Terminmarktplatz-Webhook
# Verwendung: .\scripts\test-terminmarktplatz-webhook.ps1 -BaseUrl "https://DEINE-URL" -ApiKey "DEIN-SCHLÜSSEL"

param(
    [Parameter(Mandatory=$true)]
    [string]$BaseUrl,
    [Parameter(Mandatory=$true)]
    [string]$ApiKey
)

$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = $ApiKey
    "ngrok-skip-browser-warning" = "1"
}

Write-Host "=== 1. Ping (ohne Auth) ===" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/v1/appointments/webhook/termin-marktplatz/ping" -ErrorAction Stop
    Write-Host "OK: $($r.message)" -ForegroundColor Green
} catch {
    Write-Host "FEHLER: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "WareVision/ngrok nicht erreichbar?" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== 2. Health-Check (mit API-Key) ===" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/v1/appointments/webhook/termin-marktplatz/health" -Headers $headers -ErrorAction Stop
    Write-Host "OK: $($r.message)" -ForegroundColor Green
} catch {
    Write-Host "FEHLER: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host "API-Schlüssel falsch? In WareVision Einstellungen pruefen." -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "`n=== 3. Test-Buchung senden ===" -ForegroundColor Cyan
$body = @{
    external_booking_id = "tm-test-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    starts_at = (Get-Date).AddDays(1).ToString("yyyy-MM-ddTHH:mm:ss+01:00")
    ends_at = (Get-Date).AddDays(1).AddHours(1).ToString("yyyy-MM-ddTHH:mm:ss+01:00")
    customer_first_name = "Test"
    customer_last_name = "Webhook"
    customer_email = "test-webhook@example.de"
    title = "Test-Termin (Script)"
} | ConvertTo-Json

try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/v1/appointments/webhook/termin-marktplatz" -Method POST -Headers $headers -Body $body -ErrorAction Stop
    Write-Host "OK: Termin erstellt, ID=$($r.id)" -ForegroundColor Green
    Write-Host "    Titel: $($r.title), Start: $($r.starts_at)" -ForegroundColor Gray
} catch {
    Write-Host "FEHLER: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "`n=== Fertig ===" -ForegroundColor Green
Write-Host "Terminplaner in WareVision oeffnen und pruefen." -ForegroundColor Gray
