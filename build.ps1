$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

python -m PyInstaller `
    --noconfirm `
    --clean `
    --name PrintMoney `
    --windowed `
    --icon "assets\app_icon.ico" `
    --add-data "assets;assets" `
    --collect-data customtkinter `
    --collect-data tkcalendar `
    --collect-data babel `
    --collect-data win10toast `
    --hidden-import "PIL._tkinter_finder" `
    --hidden-import "matplotlib.backends.backend_tkagg" `
    --hidden-import "plyer.platforms.win.notification" `
    --exclude-module pandas `
    --exclude-module pygame `
    main.py

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Ejecutable listo: dist\PrintMoney\PrintMoney.exe"
exit 0
