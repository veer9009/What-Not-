# Read-only process/socket correlation. Never emits command lines or credentials.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $workspace 'backend/.venv/Scripts/python.exe'
$inventoryJson = & $python (Join-Path $PSScriptRoot 'inspect_discovery_inventory.py')
if ($LASTEXITCODE -ne 0) { throw 'Read-only inventory failed; stop.' }
$inventory = ($inventoryJson -join "`n") | ConvertFrom-Json
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue |
    Where-Object LocalAddress -in @('127.0.0.1', '::1'))
$clients = @(Get-NetTCPConnection -State Established -RemotePort 5432 -ErrorAction SilentlyContinue |
    Where-Object RemoteAddress -in @('127.0.0.1', '::1'))
$correlations = @()
foreach ($connection in $inventory.connections) {
    foreach ($socket in @($clients | Where-Object LocalPort -eq $connection.client_port)) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($socket.OwningProcess)"
        if ($null -eq $process) { continue }
        $listener = @($listeners | Where-Object {
            $_.OwningProcess -eq $process.ProcessId -or $_.OwningProcess -eq $process.ParentProcessId
        })
        if ($listener.Count -eq 0) { continue }
        $listenerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener[0].OwningProcess)"
        if ($process.Name -ne 'python.exe' -or $listenerProcess.CommandLine -notmatch 'uvicorn') { continue }
        $correlations += [pscustomobject]@{
            Database = $connection.database
            WorkerProcessId = $process.ProcessId
            ParentProcessId = $process.ParentProcessId
            ListenerProcessId = $listener[0].OwningProcess
            PostgreSQLProcessId = $connection.postgres_pid
            ClientPort = $connection.client_port
            IsPython = ($process.Name -eq 'python.exe')
            IsUvicornListener = $true
        }
    }
}
if ($correlations.Count -eq 0) { throw 'No backend/database socket correlation verified; stop.' }
$result = [pscustomobject]@{
    CapturedAtUtc = [DateTime]::UtcNow.ToString('o')
    ReadOnly = $true
    ConfiguredDatabase = $inventory.configured_database
    BackendDatabaseNames = @($correlations.Database | Sort-Object -Unique)
    Connections = $correlations
}
$evidence = Join-Path $PSScriptRoot 'evidence/discovery-backend-identity.json'
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $evidence -Encoding UTF8
$result | ConvertTo-Json -Depth 5
