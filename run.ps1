<#
.SYNOPSIS
    RiaBot Dev Dashboard - launches all services in separate windows.
.USAGE
    .\run.ps1
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned  (first time only)
#>

$ProjectRoot = $PSScriptRoot

$Services = @(
    @{ Name = "Backend (Django)";  Cmd = "venv\Scripts\python manage.py runserver";                             Dir = (Join-Path $ProjectRoot "backend"); Color = "Cyan"    },
    @{ Name = "Rasa Actions";      Cmd = "venv\Scripts\python -m rasa run actions";                             Dir = (Join-Path $ProjectRoot "rasa");    Color = "Blue"    },
    @{ Name = "Rasa Core";         Cmd = 'venv\Scripts\python -m rasa run -m models --enable-api --cors "*"';  Dir = (Join-Path $ProjectRoot "rasa");    Color = "Magenta" },
    @{ Name = "Frontend";          Cmd = "npm run dev";                                                          Dir = (Join-Path $ProjectRoot "frontend"); Color = "Green"   }
)

# ---- helpers ----------------------------------------------------------------

function Write-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ____  _       ____        _   " -ForegroundColor Magenta
    Write-Host " |  _ \(_) __ _| __ )  ___ | |_ " -ForegroundColor Magenta
    Write-Host " | |_) | |/ _' |  _ \ / _ \| __|" -ForegroundColor Magenta
    Write-Host " |  _ <| | (_| | |_) | (_) | |_ " -ForegroundColor Magenta
    Write-Host " |_| \_\_|\__,_|____/ \___/ \__|" -ForegroundColor Magenta
    Write-Host ""
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "  Dev Dashboard  |  $now" -ForegroundColor DarkGray
    Write-Host "  ------------------------------------------" -ForegroundColor DarkGray
    Write-Host ""
}

function Test-Port {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch { return $false }
}

function Check-Ports {
    $checks = @(
        @{ Port = 8000; Name = "Backend (Django)"  },
        @{ Port = 5005; Name = "Rasa Core"         },
        @{ Port = 5055; Name = "Rasa Actions"      },
        @{ Port = 3000; Name = "Frontend"          }
    )
    $found = @()
    foreach ($c in $checks) {
        if (Test-Port $c.Port) { $found += "  Port $($c.Port) already in use - $($c.Name)" }
    }
    if ($found.Count -gt 0) {
        Write-Host "  [!] Port conflicts:" -ForegroundColor Yellow
        $found | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
        Write-Host ""
        $ans = Read-Host "  Continue anyway? [y/N]"
        if ($ans -notmatch "^[yY]$") { Write-Host "  Aborted." -ForegroundColor Red; exit 1 }
        Write-Host ""
    }
}

function Start-ServiceWindow {
    param($Svc)

    if (-not (Test-Path $Svc.Dir)) {
        Write-Host "  [!] Not found: $($Svc.Dir)" -ForegroundColor Red
        return $null
    }

    # Build the command that runs inside the new window
    $innerCmd = @"
`$Host.UI.RawUI.WindowTitle = 'RiaBot | $($Svc.Name)';
Set-Location '$($Svc.Dir)';
Write-Host '  Starting: $($Svc.Name)' -ForegroundColor $($Svc.Color);
Write-Host '  -----------------------------------------' -ForegroundColor DarkGray;
$($Svc.Cmd);
Write-Host '';
Write-Host '  [Exited] Press any key to close.' -ForegroundColor Yellow;
`$null = `$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
"@

    $proc = Start-Process powershell.exe `
        -ArgumentList "-NoLogo", "-NoExit", "-Command", $innerCmd `
        -PassThru

    return $proc
}

function Show-Monitor {
    param($Procs)

    Write-Host ""
    Write-Host "  Services launched. Monitoring..." -ForegroundColor Green
    Write-Host "  Press [Q] to stop all and quit." -ForegroundColor Yellow
    Write-Host "  ------------------------------------------" -ForegroundColor DarkGray
    Write-Host ""

    # Reserve lines for status block
    $lines = $Services.Count + 2
    1..$lines | ForEach-Object { Write-Host "" }

    while ($true) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq "Q") { break }
        }

        $top = [Console]::CursorTop - $lines
        if ($top -lt 0) { $top = 0 }
        [Console]::SetCursorPosition(0, $top)

        $now = Get-Date -Format "HH:mm:ss"
        Write-Host ("  Status  |  " + $now + "        ") -ForegroundColor DarkGray
        Write-Host "  ------------------------------------------" -ForegroundColor DarkGray

        for ($i = 0; $i -lt $Procs.Count; $i++) {
            $p   = $Procs[$i]
            $svc = $Services[$i]
            if ($null -eq $p) {
                Write-Host ("  [ERR] " + $svc.Name + " (not started)          ") -ForegroundColor Red
            } elseif ($p.HasExited) {
                Write-Host ("  [---] " + $svc.Name + " (exited: " + $p.ExitCode + ")   ") -ForegroundColor DarkGray
            } else {
                Write-Host ("  [ OK] " + $svc.Name + "                        ") -ForegroundColor $svc.Color
            }
        }

        Start-Sleep -Milliseconds 1000
    }
}

function Stop-All {
    param($Procs)
    Write-Host ""
    Write-Host "  Stopping all services..." -ForegroundColor Yellow
    for ($i = 0; $i -lt $Procs.Count; $i++) {
        $p   = $Procs[$i]
        $svc = $Services[$i]
        if ($null -eq $p) { continue }
        if (-not $p.HasExited) {
            Write-Host ("  Stopping " + $svc.Name + "...") -NoNewline -ForegroundColor $svc.Color
            try {
                # Kill child processes first
                Get-CimInstance Win32_Process |
                    Where-Object { $_.ParentProcessId -eq $p.Id } |
                    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                Write-Host " done." -ForegroundColor DarkGray
            } catch {
                Write-Host " (already gone)" -ForegroundColor DarkGray
            }
        }
    }
    Write-Host ""
    Write-Host "  All stopped. Goodbye!" -ForegroundColor Green
    Write-Host ""
}

# ---- main -------------------------------------------------------------------

$procs = @()

try {
    Write-Banner
    Check-Ports

    Write-Host "  Launching services..." -ForegroundColor White
    Write-Host ""

    foreach ($svc in $Services) {
        Write-Host ("  >> " + $svc.Name) -ForegroundColor $svc.Color
        $p = Start-ServiceWindow $svc
        $procs += $p
        Start-Sleep -Milliseconds 700
    }

    Show-Monitor $procs
}
finally {
    Stop-All $procs
}
