<#
Script de utilidad -- limpia los datos generados por el pipeline (data/raw
y data/processed) para poder correr los 7 scripts de punta a punta desde
cero, como en una corrida de testing.

NO toca el entorno (.venv, pyproject.toml, uv.lock) ni el codigo (scripts/) --
solo borra datos generados. El cache de kagglehub (~/.cache/kagglehub) se deja
intacto por defecto, para que el script 1 reutilice la descarga ya hecha en
vez de volver a bajarla de Kaggle en cada test. Si alguna vez queres forzar
tambien una descarga nueva desde Kaggle, corre con -LimpiarCacheKaggle.

Se corre desde la raiz del proyecto:
    .\scripts\entorno\limpiar_datos.ps1
    .\scripts\entorno\limpiar_datos.ps1 -LimpiarCacheKaggle
#>

param(
    [switch]$LimpiarCacheKaggle
)

$ErrorActionPreference = "Stop"

Write-Host "Esto va a borrar todo el contenido de:"
Write-Host "  - data/raw"
Write-Host "  - data/processed"
if ($LimpiarCacheKaggle) {
    Write-Host "  - cache de kagglehub (~/.cache/kagglehub) -- se re-descargara desde Kaggle"
}
$confirmacion = Read-Host "Escribi 'si' para confirmar"
if ($confirmacion -ne "si") {
    Write-Host "Cancelado -- no se borro nada."
    exit
}

foreach ($carpeta in @("data/raw", "data/processed")) {
    if (Test-Path $carpeta) {
        Get-ChildItem -Path $carpeta -Force | Remove-Item -Recurse -Force
        Write-Host "Vaciado: $carpeta"
    } else {
        New-Item -ItemType Directory -Path $carpeta -Force | Out-Null
        Write-Host "Creado (no existia): $carpeta"
    }
}

if ($LimpiarCacheKaggle) {
    $cacheKaggle = "$env:USERPROFILE\.cache\kagglehub"
    if (Test-Path $cacheKaggle) {
        Remove-Item -Recurse -Force $cacheKaggle
        Write-Host "Borrado: $cacheKaggle"
    }
}

Write-Host "Listo -- data/raw y data/processed quedaron vacios."