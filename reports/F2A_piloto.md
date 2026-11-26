# F2A · Prueba piloto del motor, las 12 reglas y el rollout

Generado por `scripts/pilot_f2a.py` el 2026-11-26 01:58. Fuente: generador F2B, 100 instancias por tamaño repartidas entre las 21 celdas del núcleo. Desempate: menor número de tarea (P1). Tiempo total: 11 s.

## Resumen por tamaño

| n | instancias | SBS | K_SBS | K_cóctel | K_rollout | % otro supera al SBS | % rollout < cóctel | Δ medio rollout−cóctel | % empate total | estados de decisión/inst. | % estados de decisión | ms por regla | ms cóctel | ms rollout |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 100 | R10 | 7.520 | 7.440 | 7.400 | 8.000 | 4.000 | -0.040 | 53.000 | 14.580 | 72.900 | 0.042 | 0.503 | 1.479 |
| 50 | 100 | R10 | 17.780 | 17.550 | 17.390 | 21.000 | 15.000 | -0.160 | 29.000 | 41.880 | 83.760 | 0.142 | 1.701 | 14.875 |
| 100 | 100 | R10 | 33.680 | 33.500 | 33.260 | 16.000 | 20.000 | -0.240 | 10.000 | 89.010 | 89.010 | 0.374 | 4.482 | 91.055 |


## K promedio por regla

| n | K_r1 | K_r2 | K_r3 | K_r4 | K_r5 | K_r6 | K_r7 | K_r8 | K_r9 | K_r10 | K_r11 | K_r12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20.000 | 7.590 | 7.530 | 7.750 | 7.650 | 7.860 | 7.680 | 7.680 | 7.830 | 7.650 | 7.520 | 7.630 | 7.580 |
| 50.000 | 17.880 | 17.930 | 18.250 | 17.980 | 18.600 | 17.990 | 18.260 | 18.570 | 17.990 | 17.780 | 18.030 | 18.310 |
| 100.000 | 34.210 | 34.320 | 35.220 | 34.550 | 36.080 | 34.380 | 35.130 | 35.750 | 34.490 | 33.680 | 34.590 | 34.930 |


## Tamaño del conjunto óptimo (número de instancias por tamaño del conjunto)

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 3 | 3 | 4 | 6 | 3 | 3 | 0 | 7 | 3 | 5 | 10 | 53 |
| 50 | 13 | 11 | 4 | 5 | 5 | 4 | 6 | 6 | 4 | 3 | 10 | 29 |
| 100 | 32 | 3 | 3 | 3 | 5 | 7 | 6 | 7 | 6 | 11 | 7 | 10 |


## Estimación para F3A

- Instancias previstas: 6300 (50 por celda del núcleo + 3150 ampliadas).

- Tiempo de etiquetado (cóctel + rollout) en un núcleo: ≈ 0.07 h; con 8 núcleos (joblib): ≈ 0.01 h.

- Estados de decisión por instancia: 48.5 → ≈ 305,487 estados.

- Disco estimado (instancias + estados, sin comprimir): ≈ 191 MB (presupuesto: 10 GB).


## Pendiente

- Repetir con al menos 30 instancias de Scholl (`--instances-dir data/external/scholl`) cuando estén disponibles, y ejecutar `pytest -m slow tests/core/test_cocktail_table.py` para la reproducción de la tabla del cóctel.
