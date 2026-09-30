import re

import pandas as pd
import streamlit as st

from algorithm import vehicle_assign_calculator
from services import instance_store as store

SAVED, MANUAL, UPLOAD = "Instancia guardada", "Nueva instancia", "Subir archivos"
ASSIGNMENT_PATTERN = re.compile(r"Package: (.*), Vehicle: (.*), Cost: (\d+)")

DEFAULT_VEHICLES = pd.DataFrame({"vehicle": ["v1", "v2"], "capacity": [10, 20]})
DEFAULT_PACKAGES = pd.DataFrame({"package": ["d1", "d2", "d3"], "weight": [4, 6, 8]})
DEFAULT_COSTS = {
    ("d1", "v1"): 5, ("d1", "v2"): 8,
    ("d2", "v1"): 7, ("d2", "v2"): 4,
    ("d3", "v1"): 9, ("d3", "v2"): 6,
}


def editor_records(df):
    df = df.dropna(how="all")
    return df.astype(object).where(df.notna(), None).to_dict("records")


def unique_names(records, key):
    return list(dict.fromkeys(
        str(row[key]).strip() for row in records if row.get(key) and str(row[key]).strip()
    ))


def cost_matrix_editor(package_names, vehicle_names):
    signature = (tuple(package_names), tuple(vehicle_names))
    if st.session_state.get("cost_signature") != signature:
        previous = st.session_state.setdefault("cost_values", DEFAULT_COSTS.copy())
        st.session_state.cost_base = pd.DataFrame(
            [[previous.get((package, vehicle)) for vehicle in vehicle_names] for package in package_names],
            index=package_names,
            columns=vehicle_names,
            dtype="float",
        )
        st.session_state.cost_signature = signature

    matrix = st.data_editor(
        st.session_state.cost_base,
        key=f"cost_editor_{hash(signature)}",
        width="stretch",
        column_config={
            vehicle: st.column_config.NumberColumn(vehicle, min_value=0, step=1)
            for vehicle in vehicle_names
        },
    )
    st.session_state.cost_values = {
        (package, vehicle): matrix.at[package, vehicle]
        for package in package_names
        for vehicle in vehicle_names
    }
    return [
        {"package": package, "vehicle": vehicle, "cost": value}
        for (package, vehicle), value in st.session_state.cost_values.items()
        if pd.notna(value)
    ]


def manual_rows():
    vehicles_column, packages_column = st.columns(2)
    with vehicles_column:
        st.markdown("**Vehículos**")
        vehicles = editor_records(st.data_editor(
            DEFAULT_VEHICLES,
            key="vehicles_editor",
            num_rows="dynamic",
            width="stretch",
            column_config={
                "vehicle": st.column_config.TextColumn("Vehículo", required=True),
                "capacity": st.column_config.NumberColumn("Capacidad", min_value=1, step=1, required=True),
            },
        ))
    with packages_column:
        st.markdown("**Paquetes**")
        packages = editor_records(st.data_editor(
            DEFAULT_PACKAGES,
            key="packages_editor",
            num_rows="dynamic",
            width="stretch",
            column_config={
                "package": st.column_config.TextColumn("Paquete", required=True),
                "weight": st.column_config.NumberColumn("Peso", min_value=1, step=1, required=True),
            },
        ))

    package_names = unique_names(packages, "package")
    vehicle_names = unique_names(vehicles, "vehicle")

    st.markdown("**Incompatibilidades**")
    st.caption("Pares de paquetes que no pueden viajar en el mismo vehículo. Opcional.")
    incompatible = editor_records(st.data_editor(
        pd.DataFrame(columns=store.SCHEMAS["incompatible"], dtype="object"),
        key="incompatible_editor",
        num_rows="dynamic",
        width="stretch",
        column_config={
            "package": st.column_config.SelectboxColumn("Paquete", options=package_names),
            "incompatible_package": st.column_config.SelectboxColumn("No puede ir con", options=package_names),
        },
    ))

    st.markdown("**Costos**")
    st.caption(
        "Cada fila es un paquete y cada columna un vehículo. La celda indica cuánto cuesta "
        "llevar ese paquete en ese vehículo. Déjala vacía si ese vehículo no puede llevarlo."
    )
    costs = cost_matrix_editor(package_names, vehicle_names) if package_names and vehicle_names else []

    return {"vehicles": vehicles, "packages": packages, "incompatible": incompatible, "costs": costs}


def uploaded_rows():
    st.caption("Sube archivos CSV con encabezado. `incompatible.csv` es opcional.")
    rows, missing = {}, []
    for column, (kind, headers) in zip(st.columns(len(store.SCHEMAS)), store.SCHEMAS.items()):
        file = column.file_uploader(f"{kind}.csv", type="csv", key=f"upload_{kind}", help=",".join(headers))
        if file is None:
            rows[kind] = []
            if kind not in store.OPTIONAL_FILES:
                missing.append(f"{kind}.csv")
            continue
        rows[kind] = store.parse_csv(file.getvalue().decode("utf-8-sig"), kind)

    if missing:
        st.info(f"Faltan archivos: {', '.join(missing)}.")
        return None
    return rows


def calculate(rows):
    vehicles, packages, matrix_costs = store.build_models(rows)
    solution_cost, final_solution = vehicle_assign_calculator.calculate(vehicles, packages, matrix_costs)
    assignments = [
        {"Paquete": match[1], "Vehículo": match[2], "Costo": int(match[3])}
        for match in map(ASSIGNMENT_PATTERN.fullmatch, final_solution)
        if match
    ]
    assigned = {row["Paquete"] for row in assignments}
    return {
        "rows": rows,
        "cost": solution_cost,
        "assignments": assignments,
        "assigned": len(assigned),
        "packages": len(packages),
        "unassigned": [package.name for package in packages if package.name not in assigned],
        "vehicles_used": len({row["Vehículo"] for row in assignments}),
        "load": f"{sum(p.weight for p in packages if p.name in assigned)} / {sum(v.capacity for v in vehicles.values())}",
    }


def show_result(result):
    cost, assigned, vehicles_used, load = st.columns(4)
    cost.metric("Costo total", result["cost"])
    assigned.metric("Asignados", f"{result['assigned']} / {result['packages']}")
    vehicles_used.metric("Vehículos usados", result["vehicles_used"])
    load.metric("Carga / capacidad", result["load"])

    if result["unassigned"]:
        st.warning(f"Paquetes sin asignar: {', '.join(result['unassigned'])}")

    st.subheader("Asignaciones")
    st.dataframe(result["assignments"], width="stretch", hide_index=True)


def save_form(rows):
    with st.form("save_instance", clear_on_submit=True, border=False):
        name = st.text_input("Nombre de la instancia", placeholder="exp4", help="Letras, números, '-' o '_'.")
        if st.form_submit_button("Guardar", type="primary", width="stretch"):
            try:
                store.save_instance(name.strip(), rows)
                st.toast(f"Instancia '{name.strip()}' guardada. Ya aparece en '{SAVED}'.", icon=":material/check_circle:")
            except FileExistsError:
                st.error("Ya existe una instancia con ese nombre.")
            except ValueError as error:
                st.error(str(error))


st.set_page_config(page_title="Route Planner", page_icon=":material/alt_route:", layout="wide")
st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 3rem; }
    [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.12);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-left: 4px solid #d76b35;
        border-radius: 0.5rem;
        padding: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Route Planner")
st.caption("Asigna paquetes a vehículos según capacidad, compatibilidad y costo.")

mode = st.radio("Origen de datos", [SAVED, MANUAL, UPLOAD], horizontal=True)

try:
    if mode == SAVED:
        instances = store.list_instances()
        if not instances:
            st.info("No hay instancias guardadas en data/.")
            st.stop()
        rows = store.read_instance_rows(st.selectbox("Instancia", instances))
    elif mode == MANUAL:
        rows = manual_rows()
    else:
        rows = uploaded_rows()
except (OSError, ValueError) as error:
    st.error(f"No se pudieron leer los datos: {error}")
    st.stop()

if rows is None:
    st.stop()

errors = store.validate_rows(rows)
if errors:
    st.warning("Revisa los datos antes de calcular:\n\n" + "\n".join(f"- {error}" for error in errors))

can_save = mode != SAVED
calculate_column, save_column = st.columns([3, 1]) if can_save else (st.container(), None)

with calculate_column:
    if st.button("Calcular asignación", type="primary", icon=":material/play_arrow:", disabled=bool(errors), width="stretch"):
        st.session_state.result = {**calculate(rows), "mode": mode}

if save_column:
    with save_column:
        with st.popover("Guardar como instancia", icon=":material/save:", disabled=bool(errors), width="stretch"):
            save_form(rows)

result = st.session_state.get("result")
if result and result["mode"] == mode:
    st.divider()
    if result["rows"] == rows:
        show_result(result)
    else:
        st.caption("Los datos cambiaron. Vuelve a calcular para ver el resultado actualizado.")
