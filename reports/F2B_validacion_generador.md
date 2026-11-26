# F2B · Validación del generador de instancias

Generado automáticamente por `python -m salbp_selector.gen.validate` el 2026-11-26 01:59. Semilla maestra 20261116; 100 instancias por celda del núcleo; 2000 de la capa ampliada; tiempo total 27 s.

## Resumen de criterios

| Criterio | Resultado |
|---|---|
| 1. Cumplimiento de celda (100 %) | CUMPLE (mínimo 100.0 %) |
| Tasa de rechazo < 50 % en n = 50 y 100 | CUMPLE (máximo 11.5 %) |
| 2. Parecido estructural con el conjunto público | PENDIENTE (falta el conjunto público) |
| 3. Parecido en desempeño con el conjunto público | PENDIENTE (falta el conjunto público) |
| 4. Discriminación entre reglas | 1 celdas con empate total > 90 % |
| 5. Cobertura de la capa ampliada | 0 medidas con huecos |
| 6. Reproducibilidad | CUMPLE (SHA-256 `763132d2323fa268…`) |

## 1. Cumplimiento de celda y tasa de rechazo

Comprobación independiente: se recalculan OS, cadenas y cuellos de botella desde los arcos, se valida la instancia (`validate_instance`) y se comprueba que los tiempos estén en [0,02c; c].

| cell | n | structure | os_target | time_dist | instances | compliance_pct | os_mean | os_min | os_max | chain_share_mean | n_bn_mean | rejection_rate | ms_per_instance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n20-os02-mix-pb | 20 | mixed | 0.200 | pb | 100 | 100.000 | 0.206 | 0.200 | 0.237 | 0.139 | 0.010 | 0.000 | 0.495 |
| n20-os02-mix-bm | 20 | mixed | 0.200 | bm | 100 | 100.000 | 0.208 | 0.200 | 0.237 | 0.156 | 0.050 | 0.000 | 0.509 |
| n20-os02-mix-pm | 20 | mixed | 0.200 | pm | 100 | 100.000 | 0.208 | 0.200 | 0.263 | 0.156 | 0.110 | 0.000 | 0.483 |
| n20-os06-mix-pb | 20 | mixed | 0.600 | pb | 100 | 100.000 | 0.618 | 0.600 | 0.668 | 0.155 | 0.390 | 0.000 | 0.548 |
| n20-os06-mix-bm | 20 | mixed | 0.600 | bm | 100 | 100.000 | 0.615 | 0.600 | 0.695 | 0.135 | 0.360 | 0.000 | 0.540 |
| n20-os06-mix-pm | 20 | mixed | 0.600 | pm | 100 | 100.000 | 0.618 | 0.600 | 0.679 | 0.098 | 0.380 | 0.000 | 0.541 |
| n20-os09-mix-pb | 20 | mixed | 0.900 | pb | 100 | 100.000 | 0.903 | 0.879 | 0.942 | 0.077 | 0.700 | 0.000 | 0.621 |
| n20-os09-mix-bm | 20 | mixed | 0.900 | bm | 100 | 100.000 | 0.902 | 0.863 | 0.916 | 0.085 | 0.810 | 0.000 | 0.625 |
| n20-os09-mix-pm | 20 | mixed | 0.900 | pm | 100 | 100.000 | 0.903 | 0.868 | 0.937 | 0.101 | 0.900 | 0.000 | 0.626 |
| n20-os02-ch-pb | 20 | chain | 0.200 | pb | 100 | 100.000 | 0.206 | 0.200 | 0.242 | 0.458 | 0.070 | 0.000 | 0.535 |
| n20-os02-ch-bm | 20 | chain | 0.200 | bm | 100 | 100.000 | 0.205 | 0.200 | 0.247 | 0.443 | 0.020 | 0.000 | 0.524 |
| n20-os02-ch-pm | 20 | chain | 0.200 | pm | 100 | 100.000 | 0.204 | 0.200 | 0.221 | 0.457 | 0.040 | 0.000 | 0.517 |
| n20-os06-ch-pb | 20 | chain | 0.600 | pb | 100 | 100.000 | 0.602 | 0.516 | 0.679 | 0.433 | 0.460 | 0.020 | 0.571 |
| n20-os06-ch-bm | 20 | chain | 0.600 | bm | 100 | 100.000 | 0.598 | 0.505 | 0.679 | 0.452 | 0.360 | 0.020 | 0.581 |
| n20-os06-ch-pm | 20 | chain | 0.600 | pm | 100 | 100.000 | 0.593 | 0.500 | 0.668 | 0.435 | 0.310 | 0.029 | 0.595 |
| n20-os02-bn-pb | 20 | bottleneck | 0.200 | pb | 100 | 100.000 | 0.208 | 0.200 | 0.295 | 0.053 | 1.000 | 0.000 | 0.514 |
| n20-os02-bn-bm | 20 | bottleneck | 0.200 | bm | 100 | 100.000 | 0.205 | 0.200 | 0.253 | 0.063 | 1.020 | 0.010 | 0.511 |
| n20-os02-bn-pm | 20 | bottleneck | 0.200 | pm | 100 | 100.000 | 0.207 | 0.200 | 0.247 | 0.077 | 1.000 | 0.000 | 0.661 |
| n20-os06-bn-pb | 20 | bottleneck | 0.600 | pb | 100 | 100.000 | 0.596 | 0.505 | 0.621 | 0.000 | 1.000 | 0.000 | 0.669 |
| n20-os06-bn-bm | 20 | bottleneck | 0.600 | bm | 100 | 100.000 | 0.599 | 0.521 | 0.626 | 0.000 | 1.000 | 0.000 | 0.678 |
| n20-os06-bn-pm | 20 | bottleneck | 0.600 | pm | 100 | 100.000 | 0.593 | 0.500 | 0.626 | 0.000 | 1.000 | 0.038 | 0.668 |
| n50-os02-mix-pb | 50 | mixed | 0.200 | pb | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.271 | 0.210 | 0.115 | 1.009 |
| n50-os02-mix-bm | 50 | mixed | 0.200 | bm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.256 | 0.150 | 0.074 | 1.000 |
| n50-os02-mix-pm | 50 | mixed | 0.200 | pm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.259 | 0.120 | 0.099 | 0.992 |
| n50-os06-mix-pb | 50 | mixed | 0.600 | pb | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.143 | 0.580 | 0.000 | 1.144 |
| n50-os06-mix-bm | 50 | mixed | 0.600 | bm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.156 | 0.650 | 0.000 | 1.124 |
| n50-os06-mix-pm | 50 | mixed | 0.600 | pm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.152 | 0.800 | 0.000 | 1.111 |
| n50-os09-mix-pb | 50 | mixed | 0.900 | pb | 100 | 100.000 | 0.902 | 0.900 | 0.904 | 0.120 | 1.430 | 0.000 | 1.421 |
| n50-os09-mix-bm | 50 | mixed | 0.900 | bm | 100 | 100.000 | 0.902 | 0.900 | 0.904 | 0.129 | 1.450 | 0.000 | 1.430 |
| n50-os09-mix-pm | 50 | mixed | 0.900 | pm | 100 | 100.000 | 0.902 | 0.900 | 0.904 | 0.129 | 1.380 | 0.000 | 1.439 |
| n50-os02-ch-pb | 50 | chain | 0.200 | pb | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.523 | 0.150 | 0.048 | 0.987 |
| n50-os02-ch-bm | 50 | chain | 0.200 | bm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.513 | 0.140 | 0.099 | 1.026 |
| n50-os02-ch-pm | 50 | chain | 0.200 | pm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.524 | 0.140 | 0.038 | 1.002 |
| n50-os06-ch-pb | 50 | chain | 0.600 | pb | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.449 | 0.670 | 0.010 | 1.261 |
| n50-os06-ch-bm | 50 | chain | 0.600 | bm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.448 | 0.540 | 0.010 | 1.322 |
| n50-os06-ch-pm | 50 | chain | 0.600 | pm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.439 | 0.740 | 0.010 | 1.274 |
| n50-os02-bn-pb | 50 | bottleneck | 0.200 | pb | 100 | 100.000 | 0.201 | 0.200 | 0.205 | 0.013 | 1.810 | 0.020 | 1.107 |
| n50-os02-bn-bm | 50 | bottleneck | 0.200 | bm | 100 | 100.000 | 0.201 | 0.196 | 0.205 | 0.012 | 2.060 | 0.020 | 1.122 |
| n50-os02-bn-pm | 50 | bottleneck | 0.200 | pm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.013 | 1.930 | 0.020 | 1.359 |
| n50-os06-bn-pb | 50 | bottleneck | 0.600 | pb | 100 | 100.000 | 0.601 | 0.600 | 0.605 | 0.010 | 2.270 | 0.010 | 1.427 |
| n50-os06-bn-bm | 50 | bottleneck | 0.600 | bm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.009 | 2.220 | 0.048 | 1.497 |
| n50-os06-bn-pm | 50 | bottleneck | 0.600 | pm | 100 | 100.000 | 0.601 | 0.600 | 0.605 | 0.006 | 2.000 | 0.038 | 1.474 |
| n100-os02-mix-pb | 100 | mixed | 0.200 | pb | 100 | 100.000 | 0.201 | 0.200 | 0.205 | 0.286 | 0.420 | 0.020 | 2.024 |
| n100-os02-mix-bm | 100 | mixed | 0.200 | bm | 100 | 100.000 | 0.201 | 0.200 | 0.205 | 0.279 | 0.220 | 0.020 | 2.221 |
| n100-os02-mix-pm | 100 | mixed | 0.200 | pm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.290 | 0.280 | 0.010 | 2.043 |
| n100-os06-mix-pb | 100 | mixed | 0.600 | pb | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.172 | 1.470 | 0.000 | 2.614 |
| n100-os06-mix-bm | 100 | mixed | 0.600 | bm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.161 | 1.410 | 0.000 | 2.440 |
| n100-os06-mix-pm | 100 | mixed | 0.600 | pm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.172 | 1.710 | 0.000 | 2.562 |
| n100-os09-mix-pb | 100 | mixed | 0.900 | pb | 100 | 100.000 | 0.902 | 0.900 | 0.905 | 0.147 | 2.590 | 0.000 | 3.407 |
| n100-os09-mix-bm | 100 | mixed | 0.900 | bm | 100 | 100.000 | 0.901 | 0.900 | 0.905 | 0.146 | 2.730 | 0.000 | 3.682 |
| n100-os09-mix-pm | 100 | mixed | 0.900 | pm | 100 | 100.000 | 0.902 | 0.900 | 0.905 | 0.134 | 2.230 | 0.000 | 3.680 |
| n100-os02-ch-pb | 100 | chain | 0.200 | pb | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.532 | 0.350 | 0.020 | 2.051 |
| n100-os02-ch-bm | 100 | chain | 0.200 | bm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.530 | 0.310 | 0.010 | 2.058 |
| n100-os02-ch-pm | 100 | chain | 0.200 | pm | 100 | 100.000 | 0.202 | 0.200 | 0.205 | 0.532 | 0.300 | 0.000 | 2.311 |
| n100-os06-ch-pb | 100 | chain | 0.600 | pb | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.448 | 1.140 | 0.000 | 2.775 |
| n100-os06-ch-bm | 100 | chain | 0.600 | bm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.450 | 1.220 | 0.000 | 3.073 |
| n100-os06-ch-pm | 100 | chain | 0.600 | pm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.451 | 1.270 | 0.000 | 2.800 |
| n100-os02-bn-pb | 100 | bottleneck | 0.200 | pb | 100 | 100.000 | 0.201 | 0.200 | 0.204 | 0.052 | 3.520 | 0.057 | 2.536 |
| n100-os02-bn-bm | 100 | bottleneck | 0.200 | bm | 100 | 100.000 | 0.201 | 0.200 | 0.205 | 0.053 | 3.500 | 0.057 | 2.271 |
| n100-os02-bn-pm | 100 | bottleneck | 0.200 | pm | 100 | 100.000 | 0.201 | 0.200 | 0.205 | 0.050 | 3.160 | 0.074 | 2.298 |
| n100-os06-bn-pb | 100 | bottleneck | 0.600 | pb | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.032 | 4.060 | 0.010 | 3.178 |
| n100-os06-bn-bm | 100 | bottleneck | 0.600 | bm | 100 | 100.000 | 0.602 | 0.600 | 0.605 | 0.029 | 4.060 | 0.000 | 2.915 |
| n100-os06-bn-pm | 100 | bottleneck | 0.600 | pm | 100 | 100.000 | 0.601 | 0.600 | 0.605 | 0.030 | 3.980 | 0.000 | 3.203 |


## 2 y 3. Comparación con el conjunto público de Otto et al.

Pendiente: no se encontró el conjunto público. Descargar las instancias SALBP de Otto et al. (2013) de `assembly-line-balancing.de`, copiar los `.alb` en `data/external/otto2013/` (y, si se tiene, un `cells.csv` con columnas `file,os,structure,time_dist`) y repetir con `--public-dir`. De esta comparación salen las desviaciones definitivas de PB y PM.


K promedio por regla en las instancias propias del núcleo, por tamaño (referencia para el paso 3):

| n | K_r1 | K_r2 | K_r3 | K_r4 | K_r5 | K_r6 | K_r7 | K_r8 | K_r9 | K_r10 | K_r11 | K_r12 | K_cocktail | LB1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20.000 | 7.439 | 7.406 | 7.595 | 7.542 | 7.673 | 7.532 | 7.567 | 7.634 | 7.531 | 7.364 | 7.532 | 7.510 | 7.278 | 6.577 |
| 50.000 | 17.663 | 17.643 | 18.111 | 17.826 | 18.421 | 17.819 | 18.069 | 18.290 | 17.808 | 17.468 | 17.835 | 17.965 | 17.293 | 15.691 |
| 100.000 | 34.529 | 34.613 | 35.521 | 34.833 | 36.396 | 34.811 | 35.592 | 36.080 | 34.821 | 34.107 | 34.899 | 35.369 | 33.840 | 30.931 |


## 4. Discriminación entre reglas por celda

SBS de la celda = regla con menor K promedio en la celda. Se marca la celda si el empate total (las 12 reglas con el mismo K) supera el 90 %.

| cell | instances | tie_all_pct | sbs_rule | K_sbs | K_cocktail | gap_sbs_cocktail | pct_other_beats_sbs | mean_opt_set_size | flag_tie_gt_90 |
|---|---|---|---|---|---|---|---|---|---|
| n20-os02-mix-pb | 100 | 88.000 | R1 | 4.000 | 3.960 | 0.040 | 4.000 | 11.110 | False |
| n20-os02-mix-bm | 100 | 63.000 | R10 | 5.510 | 5.450 | 0.060 | 6.000 | 10.130 | False |
| n20-os02-mix-pm | 100 | 6.000 | R10 | 12.310 | 12.100 | 0.210 | 21.000 | 5.960 | False |
| n20-os06-mix-pb | 100 | 79.000 | R1 | 4.050 | 3.990 | 0.060 | 6.000 | 10.690 | False |
| n20-os06-mix-bm | 100 | 56.000 | R1 | 5.540 | 5.500 | 0.040 | 4.000 | 10.410 | False |
| n20-os06-mix-pm | 100 | 4.000 | R10 | 12.680 | 12.500 | 0.180 | 18.000 | 5.550 | False |
| n20-os09-mix-pb | 100 | 94.000 | R1 | 4.210 | 4.210 | 0.000 | 0.000 | 11.650 | True |
| n20-os09-mix-bm | 100 | 84.000 | R2 | 5.990 | 5.990 | 0.000 | 0.000 | 11.420 | False |
| n20-os09-mix-pm | 100 | 33.000 | R10 | 13.060 | 12.980 | 0.080 | 8.000 | 8.050 | False |
| n20-os02-ch-pb | 100 | 82.000 | R2 | 4.040 | 4.000 | 0.040 | 4.000 | 10.930 | False |
| n20-os02-ch-bm | 100 | 69.000 | R1 | 5.440 | 5.370 | 0.070 | 7.000 | 10.740 | False |
| n20-os02-ch-pm | 100 | 9.000 | R10 | 12.210 | 12.060 | 0.150 | 15.000 | 6.140 | False |
| n20-os06-ch-pb | 100 | 82.000 | R12 | 4.100 | 4.070 | 0.030 | 3.000 | 11.100 | False |
| n20-os06-ch-bm | 100 | 62.000 | R2 | 5.590 | 5.520 | 0.070 | 7.000 | 10.050 | False |
| n20-os06-ch-pm | 100 | 8.000 | R10 | 12.760 | 12.560 | 0.200 | 20.000 | 5.650 | False |
| n20-os02-bn-pb | 100 | 84.000 | R10 | 3.990 | 3.970 | 0.020 | 2.000 | 11.290 | False |
| n20-os02-bn-bm | 100 | 77.000 | R1 | 5.170 | 5.160 | 0.010 | 1.000 | 10.940 | False |
| n20-os02-bn-pm | 100 | 9.000 | R10 | 12.050 | 11.910 | 0.140 | 14.000 | 5.750 | False |
| n20-os06-bn-pb | 100 | 83.000 | R2 | 4.020 | 3.970 | 0.050 | 5.000 | 10.950 | False |
| n20-os06-bn-bm | 100 | 53.000 | R10 | 5.480 | 5.430 | 0.050 | 5.000 | 10.080 | False |
| n20-os06-bn-pm | 100 | 9.000 | R10 | 12.260 | 12.130 | 0.130 | 13.000 | 6.660 | False |
| n50-os02-mix-pb | 100 | 70.000 | R1 | 9.430 | 9.380 | 0.050 | 5.000 | 10.600 | False |
| n50-os02-mix-bm | 100 | 34.000 | R1 | 12.810 | 12.680 | 0.130 | 13.000 | 8.780 | False |
| n50-os02-mix-pm | 100 | 0.000 | R10 | 29.190 | 28.890 | 0.300 | 27.000 | 2.590 | False |
| n50-os06-mix-pb | 100 | 52.000 | R1 | 9.410 | 9.360 | 0.050 | 5.000 | 10.040 | False |
| n50-os06-mix-bm | 100 | 8.000 | R1 | 12.980 | 12.910 | 0.070 | 7.000 | 7.310 | False |
| n50-os06-mix-pm | 100 | 0.000 | R10 | 30.090 | 29.960 | 0.130 | 13.000 | 2.380 | False |
| n50-os09-mix-pb | 100 | 61.000 | R9 | 9.800 | 9.710 | 0.090 | 9.000 | 9.900 | False |
| n50-os09-mix-bm | 100 | 19.000 | R1 | 13.720 | 13.530 | 0.190 | 19.000 | 7.550 | False |
| n50-os09-mix-pm | 100 | 1.000 | R10 | 32.300 | 32.050 | 0.250 | 21.000 | 4.280 | False |
| n50-os02-ch-pb | 100 | 72.000 | R2 | 9.340 | 9.310 | 0.030 | 3.000 | 10.810 | False |
| n50-os02-ch-bm | 100 | 31.000 | R10 | 12.950 | 12.870 | 0.080 | 8.000 | 9.220 | False |
| n50-os02-ch-pm | 100 | 0.000 | R10 | 29.120 | 28.900 | 0.220 | 20.000 | 2.520 | False |
| n50-os06-ch-pb | 100 | 53.000 | R11 | 9.400 | 9.290 | 0.110 | 11.000 | 9.740 | False |
| n50-os06-ch-bm | 100 | 7.000 | R1 | 13.000 | 12.810 | 0.190 | 19.000 | 7.120 | False |
| n50-os06-ch-pm | 100 | 0.000 | R10 | 30.320 | 30.010 | 0.310 | 26.000 | 2.870 | False |
| n50-os02-bn-pb | 100 | 79.000 | R2 | 9.250 | 9.250 | 0.000 | 0.000 | 10.900 | False |
| n50-os02-bn-bm | 100 | 42.000 | R10 | 12.560 | 12.500 | 0.060 | 6.000 | 9.290 | False |
| n50-os02-bn-pm | 100 | 0.000 | R10 | 28.570 | 28.280 | 0.290 | 28.000 | 2.480 | False |
| n50-os06-bn-pb | 100 | 68.000 | R1 | 9.540 | 9.480 | 0.060 | 6.000 | 10.810 | False |
| n50-os06-bn-bm | 100 | 26.000 | R1 | 12.800 | 12.690 | 0.110 | 11.000 | 8.350 | False |
| n50-os06-bn-pm | 100 | 0.000 | R10 | 29.470 | 29.290 | 0.180 | 18.000 | 2.860 | False |
| n100-os02-mix-pb | 100 | 44.000 | R1 | 18.110 | 18.040 | 0.070 | 7.000 | 9.440 | False |
| n100-os02-mix-bm | 100 | 2.000 | R1 | 25.010 | 24.960 | 0.050 | 5.000 | 6.600 | False |
| n100-os02-mix-pm | 100 | 0.000 | R10 | 56.840 | 56.550 | 0.290 | 21.000 | 1.610 | False |
| n100-os06-mix-pb | 100 | 5.000 | R1 | 18.600 | 18.530 | 0.070 | 7.000 | 7.600 | False |
| n100-os06-mix-bm | 100 | 0.000 | R1 | 25.300 | 25.240 | 0.060 | 6.000 | 5.340 | False |
| n100-os06-mix-pm | 100 | 0.000 | R10 | 58.480 | 58.370 | 0.110 | 8.000 | 1.440 | False |
| n100-os09-mix-pb | 100 | 17.000 | R1 | 18.540 | 18.460 | 0.080 | 8.000 | 7.770 | False |
| n100-os09-mix-bm | 100 | 1.000 | R1 | 26.830 | 26.660 | 0.170 | 17.000 | 5.170 | False |
| n100-os09-mix-pm | 100 | 0.000 | R10 | 62.790 | 62.530 | 0.260 | 23.000 | 2.330 | False |
| n100-os02-ch-pb | 100 | 43.000 | R2 | 18.070 | 18.050 | 0.020 | 2.000 | 9.570 | False |
| n100-os02-ch-bm | 100 | 4.000 | R10 | 25.350 | 25.240 | 0.110 | 11.000 | 7.120 | False |
| n100-os02-ch-pm | 100 | 0.000 | R10 | 56.340 | 56.130 | 0.210 | 17.000 | 1.390 | False |
| n100-os06-ch-pb | 100 | 20.000 | R1 | 18.530 | 18.370 | 0.160 | 16.000 | 8.420 | False |
| n100-os06-ch-bm | 100 | 0.000 | R1 | 25.510 | 25.270 | 0.240 | 24.000 | 5.360 | False |
| n100-os06-ch-pm | 100 | 0.000 | R10 | 59.540 | 59.330 | 0.210 | 13.000 | 1.350 | False |
| n100-os02-bn-pb | 100 | 62.000 | R2 | 17.860 | 17.840 | 0.020 | 2.000 | 9.900 | False |
| n100-os02-bn-bm | 100 | 23.000 | R10 | 24.950 | 24.880 | 0.070 | 7.000 | 7.510 | False |
| n100-os02-bn-pm | 100 | 0.000 | R10 | 55.630 | 55.330 | 0.300 | 24.000 | 1.710 | False |
| n100-os06-bn-pb | 100 | 39.000 | R1 | 18.170 | 18.110 | 0.060 | 6.000 | 9.360 | False |
| n100-os06-bn-bm | 100 | 6.000 | R1 | 24.910 | 24.790 | 0.120 | 12.000 | 7.180 | False |
| n100-os06-bn-pm | 100 | 0.000 | R10 | 58.140 | 57.970 | 0.170 | 14.000 | 1.470 | False |


## 5. Cobertura de la capa ampliada

| measure | range | instances | min | max | empty_bins_of_10 |
|---|---|---|---|---|---|
| OS (mixed) | [0.2, 0.9] | 881 | 0.201 | 0.900 | 0 |
| OS (chain) | [0.2, 0.6] | 574 | 0.200 | 0.653 | 0 |
| OS (bottleneck) | [0.2, 0.6] | 545 | 0.201 | 0.605 | 0 |
| cadenas objetivo (chain) | [0.4, 0.6] | 574 | 0.400 | 0.600 | 0 |
| cadenas objetivo (mixed) | [0.0, 0.45] | 881 | 0.000 | 0.450 | 0 |
| grado cuello de botella (n=20) | [4, 8] | 173 | 4.000 | 8.000 | 0 |
| grado cuello de botella (n=50) | [8, 14] | 170 | 8.000 | 14.000 | 0 |
| grado cuello de botella (n=100) | [8, 14] | 202 | 8.000 | 14.000 | 0 |


Tasa de rechazo en la capa ampliada por tamaño y estructura:

| n | structure | rejection_rate |
|---|---|---|
| 20 | bottleneck | 0.006 |
| 20 | chain | 0.563 |
| 20 | mixed | 0.087 |
| 50 | bottleneck | 0.029 |
| 50 | chain | 0.271 |
| 50 | mixed | 0.086 |
| 100 | bottleneck | 0.052 |
| 100 | chain | 0.047 |
| 100 | mixed | 0.057 |


![Cobertura de la capa ampliada](figures/F2B_cobertura_ampliada.png)


## 6. Reproducibilidad

Se generó dos veces el mismo lote (113 instancias) con la semilla 20261116 y se compararon los archivos `.jsonl.gz`:

- ejecución 1: `763132d2323fa2686ddc8d5b71bd20032d4e46943fda9b39ac2891b005737281`
- ejecución 2: `763132d2323fa2686ddc8d5b71bd20032d4e46943fda9b39ac2891b005737281`
- idénticos: **True**


## Supuestos y desviaciones documentadas

- Número de etapas: modo `auto` (S = 1 + f·OS·(n − 1)) mientras no se copien los valores de la Tabla 5 del artículo en `configs/generator.yaml` (`stages.fixed`).

- Longitud máxima de cadena = 5 (supuesto medido: cadenas más largas impiden alcanzar OS 0,6).

- Desviaciones de PB (0,15c) y PM (0,05c): supuestos pendientes de contrastar con el conjunto público.

- Núcleo BN: el número de cuellos de botella se sortea entre el 1 % y el 6 % de las tareas y el grado en [8, 14] ([4, 8] para n = 20), igual que en la capa ampliada.

- No se implementan módulos ni tareas aisladas (no los necesita el conjunto de referencia).
