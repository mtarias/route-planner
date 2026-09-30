# Route Planner

Aplicación para asignar paquetes a vehículos considerando peso, capacidad, incompatibilidades y costo.

## Uso web

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

La interfaz (http://localhost:8501) ofrece tres orígenes de datos:

- **Instancia guardada**: usa una carpeta de `data/`.
- **Nueva instancia**: permite cargar vehículos, paquetes, incompatibilidades y una matriz de costos (paquete × vehículo) directamente en tablas.
- **Subir archivos**: acepta los CSV descritos abajo.

Las instancias nuevas o subidas pueden guardarse en `data/` con **Guardar como instancia**.

## Uso por línea de comandos

El comando original sigue disponible:

```bash
python3 main.py exp1
```

El resultado se guarda en `results/results_<instancia>.json`.

## Formato de datos

Cada instancia es una carpeta en `data/` con estos archivos CSV (con encabezado):

- `packages.csv`: `package,weight`
- `vehicles.csv`: `vehicle,capacity`
- `incompatible.csv` (opcional): `package,incompatible_package`
- `costs.csv`: `package,vehicle,cost`

Si un paquete no tiene costo para un vehículo, ese vehículo no puede llevarlo. Cada paquete debe tener al menos un costo.

## Estrategia

La asignación utiliza una heurística codiciosa: procesa primero los paquetes más pesados y elige el menor costo disponible respetando capacidad e incompatibilidades. Es rápida, pero no garantiza una solución globalmente óptima.
