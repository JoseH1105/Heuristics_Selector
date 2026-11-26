# salbp-selector

Selección automática de heurísticos para el equilibrado de líneas de ensamble (SALBP-1) a partir de
las características de la instancia. Proyecto final de graduación (Ingeniería Mecatrónica, TEC) en el
IOC-UPC.

Estado actual: **F2A** (motor constructivo, 12 reglas y *rollout*) y **F2B** (generador de instancias
basado en SALBPGen) implementados y probados, más una app de interfaz para usar el generador.

## Estructura

```
salbp-selector/
├── pyproject.toml / requirements.txt   # paquete instalable y dependencias fijadas
├── setup_env.ps1                       # crea .venv e instala todo
├── configs/
│   ├── generator.yaml                  # parámetros del generador con su fuente
│   └── project.yaml                    # decisiones P1-P11 (valores por defecto)
├── src/salbp_selector/
│   ├── core/    # F2A: instance, io, rules, state, engine, rollout, verify
│   ├── gen/     # F2B: graphs, times, generator, validate, __main__ (CLI)
│   └── dataset/ features/ models/ evaluation/ app/   # fases siguientes (vacíos)
├── apps/generator_app.py               # app Streamlit para generar y visualizar instancias
├── scripts/pilot_f2a.py                # prueba piloto de F2A
├── tests/                              # pytest (core/ y gen/)
├── data/  runs/  models/               # no van a git (salvo data/manifests)
└── reports/                            # informes F2A_piloto.md, F2B_validacion_generador.md
```

## Entorno

Requiere Python ≥ 3.11 (probado con 3.12).

```powershell
powershell -ExecutionPolicy Bypass -File setup_env.ps1          # crea .venv, instala y pasa las pruebas
powershell -ExecutionPolicy Bypass -File setup_env.ps1 -Torch cuda   # además, PyTorch con CUDA
```

Al abrir la carpeta `salbp-selector` en VS Code se usa `.venv` automáticamente
(`.vscode/settings.json`); el panel de pruebas detecta pytest y en *Run and Debug* están
configurados la app, el generador, la validación y el piloto.

## Uso

Generar instancias (por defecto, la base de F3A: 50 por celda del núcleo + 3150 ampliadas):

```powershell
python -m salbp_selector.gen --config configs/generator.yaml --core-per-cell 50 --extended 3150 --out data/raw/instances/
```

Salida: `data/raw/instances/all/n{n}/{core,extended}.jsonl.gz` y `generation_log.json` (configuración,
tasas de rechazo por celda y SHA-256 de cada archivo). `--format json` escribe un `.json` por instancia.

App de interfaz (generar, cargar `.json`/`.alb`/`.IN2`, ver el grafo por etapas, tareas, tiempos,
soluciones de las 12 reglas, cóctel y *rollout*, generar lotes y guardar):

```powershell
streamlit run apps/generator_app.py
```

Validación del generador y piloto del motor:

```powershell
python -m salbp_selector.gen.validate --per-cell 100 --extended 2000 [--public-dir data/external/otto2013]
python scripts/pilot_f2a.py --per-size 100
python -m pytest              # pruebas rápidas
python -m pytest -m slow      # rendimiento, tasa de rechazo y tabla del cóctel (requiere Scholl)
```

Uso del motor desde Python:

```python
from salbp_selector.core import load_instance, run_rule, run_cocktail, run_rollout
from salbp_selector.gen import CellSpec, generate

inst = generate(CellSpec(n=50, os_target=0.6, structure="mixed", time_dist="bm"), seed=1)
run_rule(inst, 1).K, run_cocktail(inst)["K_min"], run_rollout(inst).K
```

## Datos externos pendientes

- 269 instancias de Scholl → `data/external/scholl/` (`.alb`, o `.IN2` + `cycle_times.csv`) para la
  prueba de reproducción de la tabla del cóctel.
- Conjunto de Otto et al. (2013) → `data/external/otto2013/` para los criterios 2 y 3 de la validación.
- Valores de la Tabla 5 del artículo (número de etapas) → `configs/generator.yaml`, `stages.fixed`.
