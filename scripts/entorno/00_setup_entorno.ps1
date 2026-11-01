$ErrorActionPreference = "Stop"
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "Inicializando proyecto uv..."
    uv init --no-workspace
} else {
    Write-Host "pyproject.toml ya existe -- no se reinicializa."
}
$carpetas = @("data/raw", "data/processed", "reports/figuras", "assets/fonts/Montserrat")
foreach ($carpeta in $carpetas) {
    if (-not (Test-Path $carpeta)) {
        New-Item -ItemType Directory -Path $carpeta -Force | Out-Null
        Write-Host "Creada carpeta: $carpeta"
    }
}
$paquetes = @(
    "kagglehub",    # script 1: descarga del dataset
    "ipywidgets",   # barra de progreso de tqdm en la consola de IPython/Positron
    "pandas",       # script 2 en adelante: manipulacion de datos
    "pyarrow",      # d06: guardar panel_predictores/dataset_modelable en .parquet
    "matplotlib",   # e01: graficos del analisis exploratorio
    "scipy",        # e01: pandas.Series.corr(method="spearman") lo requiere por debajo
    "scikit-learn"  # analisis PCA
)
Write-Host "Instalando/actualizando dependencias: $($paquetes -join ', ')"
uv add @paquetes
Write-Host ""
Write-Host "Listo. Para que Positron use este entorno:"
Write-Host "  Ctrl+Shift+P -> 'Python: Select Interpreter' -> .venv\Scripts\python.exe"
Write-Host ""
Write-Host "Pendiente manual (una sola vez): bajar la tipografia Montserrat"
Write-Host "  (.ttf) y dejarla en assets/fonts/Montserrat/ -- ver instrucciones"
Write-Host "  del script scripts/eda/e01_analisis_exploratorio.py."