# app/models/opsa.py  # OPSA: cálculo de condition, confidence y discretización estable

import os  # rutas de archivos
import json  # conversión a GeoJSON (dict)
from typing import List, Tuple, Dict  # tipado
import numpy as np  # cálculo numérico
import pandas as pd  # manejo tabular
import geopandas as gpd  # geodatos

# Mapeo maestro: área -> { etiqueta_UI -> (col_EV, [col_CO]) }
FIELD_MAP: Dict[str, Dict[str, Tuple[str, List[str]]]] = {
    "Irish_Sea": {
        "Benthic habitats":      ("EV_Benth",   ["CO_Benth"]),
        "Demersal fish":         ("EV_Demfish", ["CO_Demfish"]),
        "Macrozoobenthos":       ("EV_Maczoo",  ["CO_Maczoo"]),
    },
    "North_Sea": {
        "Benthic habitats":      ("EV_habitat", ["CO_habitat"]),
        "Macrozoobenthos":       ("EV_benthos", ["CO_benthos"]),
    },
    "Santander": {
        "Subtidal macroalgae":        ("EV_Submacr", ["CO_Submacr"]),
        "Intertidal macroalgae":      ("EV_Intmacr", ["CO_Intmacr"]),
        "Benthic macroinvertebrates": ("EV_Macinv",  ["CO_Macinv"]),
        "Benthic habitats":           ("EV_Behab",   ["CO_Behab"]),
        "Angiosperms":                ("EV_Angio",   ["CO_Angio"]),
    },
}

def _area_to_parquet_path(area: str) -> str:
    base = os.path.join(os.getcwd(), "results", "opsa", area)  # carpeta por área
    fname_map = {
        "Irish_Sea": "eunis_irish_sea.parquet",
        "North_Sea": "eunis_north_sea.parquet",
        "Santander": "eunis_santander.parquet",
    }
    if area not in fname_map:  # validar área soportada
        raise ValueError(f"Área no soportada: {area}")  # error informativo
    path = os.path.join(base, fname_map[area])  # construir ruta
    if not os.path.exists(path):  # verificar existencia
        raise FileNotFoundError(f"No se encontró el GeoParquet EUNIS: {path}")  # error claro
    return path  # devolver ruta válida

def _ensure_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:  # comprobar CRS
        raise ValueError("El GeoParquet no tiene CRS definido.")  # error si falta
    if gdf.crs.to_epsg() != 4326:  # si no es WGS84
        gdf = gdf.to_crs(4326)  # reproyectar a EPSG:4326
    return gdf  # devolver gdf con CRS correcto

def _find_existing_column(candidates: List[str], columns: List[str]) -> str:
    idx = {c.lower(): c for c in columns}  # índice insensible a mayúsculas
    for cand in candidates:  # recorrer candidatos en orden
        real = idx.get(cand.lower())  # buscar equivalente real
        if real:  # si existe
            return real  # devolver nombre real
    return ""  # devolver vacío si no hay coincidencia

# API 1: calcular la condition media segun las componentes que pasa el usuario:
def compute_condition_mean(
    study_area: str,  # área elegida en el UI
    components: List[str],  # EC seleccionados
    out_field_condition: str = "condition",  # nombre campo condición
    out_field_confidence: str = "confidence",  # nombre campo confianza
    out_field_class: str = "condition_class",  # nombre campo clase discreta
    persist: bool = True  # si True, guardar cambios en el mismo parquet
) -> Tuple[Dict, str]:
    if not components:  # validar selección
        raise ValueError("Debes seleccionar al menos un Ecosystem Component.")  # error claro

    parquet_path = _area_to_parquet_path(study_area)  # localizar parquet del área
    gdf = gpd.read_parquet(parquet_path)  # leer geo-parquet
    gdf = _ensure_wgs84(gdf)  # asegurar WGS84

    if study_area not in FIELD_MAP:  # validar mapeo disponible
        raise KeyError(f"No hay mapeo de columnas para el área: {study_area}")  # error

    area_map = FIELD_MAP[study_area]  # mapeo de columnas para el área
    ev_list: List[pd.Series] = []  # series EV limpias (NaN donde NoData)
    co_list: List[pd.Series] = []  # series CO limpias (alineadas con EV)
    labels_used: List[str] = []  # etiquetas utilizadas (para depurar)
    missing: List[str] = []  # componentes sin columnas válidas

    for label in components:  # recorrer componentes seleccionados
        if label not in area_map:  # si el label no está mapeado
            missing.append(f"{label} (sin mapeo en {study_area})")  # anotar fallo
            continue  # siguiente componente

        ev_name, co_candidates = area_map[label]  # columnas esperadas
        ev_col = _find_existing_column([ev_name], list(gdf.columns))  # resolver EV real
        co_col = _find_existing_column(co_candidates, list(gdf.columns))  # resolver CO real (puede no existir)

        if not ev_col:  # si no hay EV en el parquet
            missing.append(f"{label} -> {ev_name}")  # anotar columna ausente
            continue  # siguiente

        s_ev = pd.to_numeric(gdf[ev_col], errors="coerce").astype(float)  # convertir EV a float
        s_ev = s_ev.mask(s_ev == 0)  # EV==0 se considera NoData → NaN

        if co_col:  # si existe CO
            s_co = pd.to_numeric(gdf[co_col], errors="coerce").astype(float)  # convertir CO a float
            s_co = s_co.mask((s_co == 0) | s_co.isna())  # CO==0/NaN → NoData
        else:
            s_co = pd.Series(np.nan, index=gdf.index)  # si no hay CO, todo NaN

        s_co = s_co.mask(s_ev.isna())  # si EV es NaN, también ignorar CO

        ev_list.append(s_ev)  # acumular EV limpio
        co_list.append(s_co)  # acumular CO limpio
        labels_used.append(label)  # registrar etiqueta usada

    if missing and not ev_list:  # si nada válido
        detalle = "; ".join(missing)  # texto de error
        raise KeyError(f"No se encontraron columnas EV/CO válidas: {detalle}")  # error informativo

    if not ev_list:  # seguridad adicional
        raise ValueError("No se pudo calcular la condición: ninguna serie válida tras filtrar NoData.")  # error

    ev_df = pd.concat(ev_list, axis=1)  # DataFrame con EV por columna
    ev_df.columns = labels_used  # nombrar columnas con etiquetas
    co_df = pd.concat(co_list, axis=1)  # DataFrame con CO por columna
    co_df.columns = labels_used  # mismo orden

    cond = ev_df.mean(axis=1, skipna=True)  # media EV por fila ignorando NaN
    conf = co_df.mean(axis=1, skipna=True)  # media CO por fila ignorando NaN
    cond = cond.clip(lower=0, upper=5)  # acotar a 0–5
    # conf puede estar en [0,1] o similar según tus datos; la dejamos tal cual tras NaN→promedio
    gdf[out_field_condition] = cond.astype(float)  # escribir condición
    gdf[out_field_confidence] = conf.astype(float)  # escribir confianza

    # Discretización estable en servidor:
    # 0 -> NoData ; 1:(0,1] ; 2:(1,2] ; 3:(2,3] ; 4:(3,4] ; 5:(4,5]
    cond_valid = cond.where(cond > 0, np.nan)  # tratar ≤0 como NoData
    bins = [0, 1, 2, 3, 4, 5]  # límites de clases
    labels = [1, 2, 3, 4, 5]  # etiquetas de clase
    cls = pd.cut(cond_valid, bins=bins, labels=labels, right=True, include_lowest=False)  # clasificar
    cls = cls.astype("float")  # pasar a float (por NaN en cut)
    cls = cls.fillna(0).astype(int)  # NaN→0 (NoData), y entero
    gdf[out_field_class] = cls  # escribir clase discreta

    # Diagnóstico (opcional):
    try:
        counts = gdf[out_field_class].value_counts().sort_index()
        print(f"OPSA DEBUG ➜ clases (0..5): {dict(counts)}")
    except Exception:
        pass

    if persist:  # si hay que guardar de vuelta
        gdf.to_parquet(parquet_path, compression="zstd")  # persistir cambios

    geojson_dict = json.loads(gdf.to_json())  # exportar GeoJSON como dict
    return geojson_dict, parquet_path  # devolver datos y ruta

# API 2: resumen ponderado por tipo de habitat

def compute_summary_by_habitat_type(  # calcular resumen por 'habitat type' del parquet enriquecido
    parquet_path: str,  # ruta al parquet (el mismo que actualiza compute_condition_mean)
    study_area: str,  # área (para convertir 'area' a hectáreas correctamente)
    group_field: str = "AllcombD"  # nombre exacto del campo de agrupación (p.ej. 'x')
) -> pd.DataFrame:  # devuelve DataFrame con columnas: group, condition_wavg, confidence_wavg, area_ha
    # Leer el parquet ya enriquecido con 'condition' y 'confidence'
    gdf = gpd.read_parquet(parquet_path)  # leer GeoParquet
    # Validar columnas mínimas
    needed = {group_field, "area", "condition", "confidence"}  # conjunto de columnas imprescindibles
    missing = [c for c in needed if c not in gdf.columns]  # detectar ausentes
    if missing:  # si faltan columnas
        raise KeyError(f"Faltan columnas en el parquet para el resumen: {missing}")  # error claro

    # Convertir área a hectáreas según el área de estudio
    if study_area == "": 
        area_ha = pd.to_numeric(gdf["area"], errors="coerce").astype(float)  # km² → km²
    else:  # North_Sea y Santander: 'area' en km²
        area_ha = pd.to_numeric(gdf["area"], errors="coerce").astype(float) / 1000000.0  # m² → km2

    # Preparar valores como float
    cond = pd.to_numeric(gdf["condition"], errors="coerce").astype(float)  # condición
    conf = pd.to_numeric(gdf["confidence"], errors="coerce").astype(float)  # confianza
    # Tratamiento de NoData: condición ≤ 0 se ignora (NaN) en el promedio
    cond = cond.where(cond > 0, np.nan)  # ≤0 → NaN (NoData)

    # DataFrame auxiliar con columnas necesarias
    df = pd.DataFrame({
        "group": gdf[group_field].astype(str),  # la categoría de 'x' como string legible
        "area_km": area_ha,  # área en hectáreas
        "condition": cond,  # condición filtrada
        "confidence": conf,  # confianza (tal cual; si es NaN, se ignora en promedio)
    })

    # Función interna de media ponderada robusta
    def _wavg(values: pd.Series, weights: pd.Series) -> float:  # calcular media ponderada ignorando NaN y pesos <=0
        v = values.to_numpy(dtype="float64")  # a numpy
        w = weights.to_numpy(dtype="float64")  # a numpy
        m = np.isfinite(v) & np.isfinite(w) & (w > 0)  # máscara de válidos
        if not m.any():  # si no hay válidos
            return float("nan")  # devolver NaN
        return float(np.average(v[m], weights=w[m]))  # media ponderada

    # Agregar por 'group'
    groups = []  # lista de registros de salida
    for name, sub in df.groupby("group"):  # agrupar por valor de 'x'
        a = sub["area_km"]  # pesos (ha)
        c = sub["condition"]  # condición
        f = sub["confidence"]  # confianza
        wa_c = _wavg(c, a)  # condition ponderada por área
        wa_f = _wavg(f, a)  # confidence ponderada por área
        area_sum = float(np.nansum(a.to_numpy(dtype="float64")))  # suma de áreas (ha)
        groups.append({  # añadir registro
            "group": str(name),  # nombre de categoría
            "condition_wavg": wa_c,  # condición media ponderada
            "confidence_wavg": wa_f,  # confianza media ponderada
            "area_km": area_sum  # extensión en ha
        })

    # Construir DataFrame final ordenado por 'group'
    out = pd.DataFrame(groups).sort_values("group").reset_index(drop=True)  # ordenar y reindexar
    return out  # devolver resumen tabular listo para graficar