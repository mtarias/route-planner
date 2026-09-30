import csv
import io
import re
from pathlib import Path

from models import cost as cost_model
from models import package as package_model
from models import vehicle as vehicle_model

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")

SCHEMAS = {
    "vehicles": ["vehicle", "capacity"],
    "packages": ["package", "weight"],
    "incompatible": ["package", "incompatible_package"],
    "costs": ["package", "vehicle", "cost"],
}
OPTIONAL_FILES = {"incompatible"}
NUMERIC_COLUMNS = {"capacity", "weight", "cost"}


def instance_path(name):
    if not NAME_PATTERN.fullmatch(name or ""):
        raise ValueError("Nombre inválido: usa solo letras, números, '-' o '_' (máx. 50).")
    return DATA_ROOT / name


def list_instances():
    return sorted(
        path.name for path in DATA_ROOT.iterdir()
        if path.is_dir() and (path / "packages.csv").exists()
    )


def parse_csv(text, kind):
    expected = SCHEMAS[kind]
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not rows or [cell.strip().lower() for cell in rows[0]] != expected:
        raise ValueError(f"{kind}.csv debe tener el encabezado: {','.join(expected)}")

    records = []
    for line, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(expected):
            raise ValueError(f"{kind}.csv, línea {line}: se esperaban {len(expected)} columnas.")
        records.append(dict(zip(expected, (cell.strip() for cell in row))))
    return records


def read_instance_rows(name):
    path = instance_path(name)
    rows = {}
    for kind in SCHEMAS:
        file = path / f"{kind}.csv"
        if not file.exists():
            if kind in OPTIONAL_FILES:
                rows[kind] = []
                continue
            raise FileNotFoundError(f"Falta el archivo {file.relative_to(DATA_ROOT.parent)}")
        rows[kind] = parse_csv(file.read_text(encoding="utf-8"), kind)
    return rows


def save_instance(name, rows):
    path = instance_path(name)
    path.mkdir(exist_ok=False)
    for kind, columns in SCHEMAS.items():
        with open(path / f"{kind}.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(columns)
            writer.writerows(
                [_as_int(row[column]) if column in NUMERIC_COLUMNS else _text(row[column]) for column in columns]
                for row in rows.get(kind, [])
            )
    return path


def _as_int(value):
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return int(str(value).strip())


def _text(value):
    return "" if value is None else str(value).strip()


def _check_int(value, label, minimum, errors):
    try:
        number = _as_int(value)
    except (TypeError, ValueError):
        errors.append(f"{label}: valor inválido '{_text(value)}'.")
        return None
    if number < minimum:
        errors.append(f"{label}: debe ser mayor o igual a {minimum}.")
        return None
    return number


def _check_names(records, key, label, errors):
    names = set()
    for index, row in enumerate(records, start=1):
        name = _text(row.get(key))
        if not name:
            errors.append(f"{label}, fila {index}: falta el nombre.")
        elif name in names:
            errors.append(f"{label} repetido: {name}.")
        names.add(name)
    names.discard("")
    if not names:
        errors.append(f"Debe haber al menos un registro en {label.lower()}.")
    return names


def validate_rows(rows):
    errors = []
    vehicles = _check_names(rows["vehicles"], "vehicle", "Vehículos", errors)
    packages = _check_names(rows["packages"], "package", "Paquetes", errors)

    for row in rows["vehicles"]:
        _check_int(row.get("capacity"), f"Capacidad de {_text(row.get('vehicle'))}", 1, errors)
    for row in rows["packages"]:
        _check_int(row.get("weight"), f"Peso de {_text(row.get('package'))}", 1, errors)

    for index, row in enumerate(rows.get("incompatible", []), start=1):
        first, second = _text(row.get("package")), _text(row.get("incompatible_package"))
        if first not in packages or second not in packages:
            errors.append(f"Incompatibilidades, fila {index}: paquete inexistente.")
        elif first == second:
            errors.append(f"Incompatibilidades, fila {index}: un paquete no puede ser incompatible consigo mismo.")

    packages_with_cost = set()
    for index, row in enumerate(rows["costs"], start=1):
        package, vehicle = _text(row.get("package")), _text(row.get("vehicle"))
        if package not in packages or vehicle not in vehicles:
            errors.append(f"Costos, fila {index}: paquete o vehículo inexistente ({package}, {vehicle}).")
        elif _check_int(row.get("cost"), f"Costo {package}/{vehicle}", 0, errors) is not None:
            packages_with_cost.add(package)

    missing = sorted(packages - packages_with_cost)
    if missing:
        errors.append(f"Paquetes sin ningún costo: {', '.join(missing)}.")
    return errors


def build_models(rows):
    vehicles = {
        _text(row["vehicle"]): vehicle_model.Vehicle(_text(row["vehicle"]), _as_int(row["capacity"]))
        for row in rows["vehicles"]
    }

    # The algorithm supports a single incompatible package per package.
    incompatibles = {}
    for row in rows.get("incompatible", []):
        first, second = _text(row["package"]), _text(row["incompatible_package"])
        incompatibles[first] = second
        incompatibles[second] = first

    packages = [
        package_model.Package(_text(row["package"]), _as_int(row["weight"]), incompatibles.get(_text(row["package"]), []))
        for row in rows["packages"]
    ]
    packages_by_name = {package.name: package for package in packages}

    matrix_costs = {}
    for row in rows["costs"]:
        package_name = _text(row["package"])
        cost = cost_model.Cost(packages_by_name[package_name], vehicles[_text(row["vehicle"])], _as_int(row["cost"]))
        matrix_costs.setdefault(package_name, []).append(cost)

    return vehicles, packages, matrix_costs


def load_instance(name):
    rows = read_instance_rows(name)
    errors = validate_rows(rows)
    if errors:
        raise ValueError("\n".join(errors))
    return build_models(rows)
