# Estimador de Flujos en Supermanzanas

Genera una matriz Origen–Destino (OD) interna para una supermanzana tratada como **sistema cerrado**, a partir de:

1. **Conteos de accesos** de entrada (producciones, G) y salida (atracciones, A), en veh/h, y
2. **Costos de viaje** (tiempo) entre cada par entrada→salida calculados sobre la red SUMO con TraCI.

La matriz OD resultante puede alimentar un flujo de ruteo/simulación (p. ej., con `duaIterate.py` en SUMO) para estimar flujos internos calle por calle.

---

## Fundamento teórico

### 1) Modelo de gravedad con impedancia exponencial

Se estima un flujo bruto para cada par (i, j) (entrada i, salida j):

$T_{ij}^{*} = G_i \, A_j \, e^{-\beta \; c_{ij}}$

* **Gi**: producción (conteo de entrada) en el acceso i.
* **Aj**: atracción (conteo de salida) en el acceso j.
* **cij**: costo (tiempo de viaje en s) de ir de i → j por la red.
* **β**: parámetro de fricción (>0) que controla cuánto “castiga” los viajes largos (en el código, por defecto `BETA=0.2`).

### 2) Balanceo para respetar totales (cerrar el sistema)

Como queremos **respetar los totales observados** $\sum_j T_{ij}=G_i$ y $\sum_i T_{ij}=A_j$, se normaliza en dos pasos:

1. **Por filas**: se escala $T_{ij}^{*}$ para que cada fila sume $G_i$.
2. **Por columnas**: se reescala para que cada columna sume $A_j$.

> Nota: En esta implementación se hace **una pasada** fila→columna. Si se busca mayor precisión, puede iterarse (método IPF/Fratar) hasta converger simultáneamente en filas y columnas.

### 3) Red + costos realistas

Los **costos** $c_{ij}$ se obtienen llamando a SUMO vía TraCI (`traci.simulation.findRoute`) sobre la red cargada, y tomando el `travelTime` de la ruta más barata.

Si no existe ruta entre un par (i, j), el costo se considera ausente y el flujo se fija en 0.

---

## Arquitectura mínima

```
project_root/
├── main.py                      # Lanza la GUI PyQt5
├── models/
│   └── distribution.py          # Lógica OD: costos, lectura de conteos, gravedad
└── ui/
    └── interface.py             # Clase Ui_MainWindow (Qt Designer)
```

> **Importante**: Los nombres de los **edges** de contorno en la red SUMO deben seguir el patrón:
>
> * Entradas: `in_...`
> * Salidas: `out_...`
>
> El script detecta automáticamente `ORIGINS = edges con 'in_'` y `DESTINATIONS = edges con 'out_'`.

---

## Requisitos

* **Python 3.11+** (recomendado)
* **SUMO** instalado y el binario `sumo` disponible en el `PATH`
  (el código invoca `sumo` headless; no usa `sumo-gui`).
* Paquetes Python:

  * `PyQt5`
  * `pandas`
  * `numpy`
  * `traci` (viene con SUMO; puede instalarse desde `sumo/tools` o vía pip según distribución)

Ejemplo de instalación de dependencias Python:

```bash
pip install PyQt5 pandas numpy
# Asegúrate de tener SUMO y TraCI disponibles
```

---

## Formato del archivo de conteos (.xlsx)

La hoja debe contener **cabecera** y, como mínimo, estas columnas:

* `tipo_acceso`: **`in`** para entradas o **`out`** para salidas.
* `sentido`: cardinal del borde (ej.: `N`, `S`, `E`, `O`).
* `avenida`: nombre/etiqueta del acceso (sin espacios idealmente).
* `conteo_veh_h`: conteo en **vehículos/hora**.

El programa genera internamente un `access_id = tipo_acceso + '_' + sentido + '_' + avenida`,
por ejemplo: `in_N_AvenidaA` o `out_E_AvenidaF`.

**Ejemplo (fila):**

| tipo\_acceso | sentido | avenida | conteo\_veh\_h |
| ------------ | ------- | ------- | -------------- |
| in           | N       | AvA     | 450            |
| out          | E       | AvF     | 380            |

> Los `in_` se interpretan como **producciones** (G) y los `out_` como **atracciones** (A).

---

## Red SUMO (.net.xml)

* El selector de archivo espera un `.xml` de SUMO (p. ej., `mi_red.net.xml`).
* Asegúrate de que los **edges de contorno** estén correctamente **nombrados** con `in_` y `out_`.
* Los tiempos de viaje se calculan con la red cargada y sus atributos (límites de velocidad, conexiones, prohibiciones, etc.).

---

## Uso (GUI)

1. **Ejecuta**:

   ```bash
   python main.py
   ```
2. En la ventana:

   * **Selecciona Excel** de conteos (`*.xlsx`).
   * **Selecciona red SUMO** (`*.xml`).
   * Presiona **Iniciar**.
3. La barra de estado mostrará *“¡Proceso finalizado con éxito!”* y en consola se imprimirá la **suma total de viajes** estimados.

**¿Qué produce?**
Una **DataFrame** con columnas: `origen`, `destino`, `viajes`, donde `viajes` está **redondeado a entero**.

> Si prefieres **conteos estocásticos**, puedes cambiar la línea comentada por Poisson en `distribution.py`:
>
> ```python
> # df_od['viajes'] = df_od['viajes'].apply(lambda x: np.random.poisson(x))
> ```

---

## API principal (resumen)

* `contours_finder(netfile) -> (ORIGINS, DESTINATIONS)`

  * Lee el `.net.xml` y devuelve listas de edges con prefijos `in_` y `out_`.
* `costs_matrix(origins, destinations, netfile) -> dict`

  * Lanza `sumo` vía TraCI y calcula `travelTime` de i→j. Devuelve `costs[(i,j)] = tiempo`.
* `read_counts(excel_path) -> (G, A)`

  * Convierte el Excel en dos diccionarios: `G[access_id_in] = veh/h`, `A[access_id_out] = veh/h`.
* `gravity_model(G, A, costs, BETA=0.2) -> DataFrame`

  * Aplica gravedad + balanceo (fila y columna), retorna DataFrame `origen, destino, viajes`.

---

## Suposiciones y limitaciones

* **Sistema cerrado**: la suma de `G` debiera ser cercana a la suma de `A`. Si difieren mucho, el balanceo forzará ajustes.
* **Balanceo simple (1 pasada)**: puede no igualar perfectísimamente ambos marginales. Para mayor fidelidad, integrar IPF iterativo.
* **Prefijos `in_`/`out_` obligatorios** en los IDs de edges y accesos (Excel) para el mapeo automático.
* **Rutas inexistentes**: pares sin ruta quedan en 0.
* **Unidades**: `conteo_veh_h` en veh/h; `cij` en segundos (por `travelTime`). β está en `1/seg`.

---

## Checklist de problemas comunes

* `sumo` no encontrado → agrega SUMO al `PATH` o ajusta `sumo_binary` en `distribution.py`.
* Excel con columnas distintas → asegúrate de usar exactamente: `tipo_acceso, sentido, avenida, conteo_veh_h`.
* Edges sin prefijos `in_`/`out_` → renombra en la red o adapta `contours_finder`.
* Totales G ≠ A → revisa conteos o considera aplicar IPF multipasada.

---

## Próximos pasos sugeridos (opcionales)

* **IPF/Fratar iterativo** con umbral de convergencia.
* **Exportar OD** a formato SUMO (trips/routes) y ejecutar `duaIterate.py` automáticamente.
* **Parámetro β calibrable** desde GUI y por periodo horario.
* **Soporte estocástico** (Poisson) con control de semilla.
* **Validación** con conteos internos puntuales (si existen).

---

## Licencia

Pendiente de definir por el autor del proyecto.
