import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import numpy as np
import pandas as pd

from modules.plotter.map import Map
from modules.plotter.bar_chart_3d import BarChart3D


# ============================================================================
# EJEMPLO 1: BarChart3D
# ============================================================================


def example_barchart_fluent_api():
    """Ejemplo de gráfico 3D usando sin create_plot()."""

    # Crear datos de ejemplo
    df = pd.DataFrame(
        {
            "x": [10, 10, 20, 20, 30, 30],
            "y": [0.1, 0.1, 0.2, 0.2, 0.3, 0.3],
            "z": [5, 3, 7, 4, 6, 2],
            "epsilon": [0.5, 1.0, 0.5, 1.0, 0.5, 1.0],
        }
    )

    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    # Crear gráfico usando (como Map)
    chart = BarChart3D(
        df=df,
        key_dict=key_dict,
        figsize=(12, 10),
        n_xticks=5,
        n_yticks=5,
        fmt_scale=1.2,
    )

    # Construir el gráfico paso a paso
    chart.add_bars(colormap_name="viridis", alpha=0.9, edgecolor="black")
    chart.add_colorbar(label="epsilon (ε)")
    chart.set_labels(
        x_label="Distancia (km)", y_label="Profundidad (km)", z_label="Magnitud"
    )
    chart.set_limits(invert_x=True)
    chart.set_view(elev=20, azim=45)

    # Guardar
    chart.save_plot("dev/outputs/barchart_fluent", formats=["png", "svg"])
    print("BarChart3D creado ")


# ============================================================================
# EJEMPLO 2: BarChart3D - Construcción Mínima
# ============================================================================


def example_barchart_minimal():
    """Ejemplo mínimo de gráfico 3D."""

    df = pd.DataFrame(
        {
            "x": [10, 20, 30],
            "y": [0.1, 0.2, 0.3],
            "z": [5, 7, 6],
            "epsilon": [0.5, 1.0, 1.5],
        }
    )

    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    # Construcción mínima
    chart = BarChart3D(df, key_dict, figsize=(10, 10))
    chart.add_bars()  # Usa defaults
    chart.add_colorbar()
    chart.set_labels("X", "Y", "Z")
    chart.set_limits()

    chart.save_plot("dev/outputs/barchart_minimal", formats=["png"])
    print("BarChart3D mínimo creado")


# ============================================================================
# EJEMPLO 3: BarChart3D - Personalización Avanzada
# ============================================================================


def example_barchart_advanced():
    """Ejemplo avanzado con personalización completa."""

    # Datos más complejos
    np.random.seed(42)
    data = []
    for x in [10, 20, 30, 40, 50]:
        for y in [0.1, 0.2, 0.3]:
            for eps in [0.5, 1.0, 1.5, 2.0]:
                z = np.random.uniform(2, 8)
                data.append({"x": x, "y": y, "z": z, "epsilon": eps})

    df = pd.DataFrame(data)
    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    chart = BarChart3D(
        df=df,
        key_dict=key_dict,
        dx=8,  # Barras más anchas
        dy=0.08,
        figsize=(16, 12),
        fmt_scale=1.5,
        n_xticks=6,
        n_yticks=5,
    )

    # Personalización completa
    chart.add_bars(colormap_name="plasma", alpha=0.85, edgecolor="darkgray")
    chart.add_colorbar(label="Factor ε")
    chart.set_labels(
        x_label="Distancia (km)", y_label="Profundidad (km)", z_label="Intensidad"
    )
    chart.set_limits(invert_x=True)
    chart.set_view(elev=25, azim=60)

    # Añadir texto informativo
    chart.add_text(
        text="Análisis 3D\nN=60 muestras",
        position={"x": 0.02, "y": 0.95},
    )

    chart.save_plot("dev/outputs/barchart_advanced", formats=["png", "svg"])
    print("BarChart3D avanzado creado")


# ============================================================================
# EJEMPLO 4: Map
# ============================================================================


def example_map_fluent_api():
    """Ejemplo de mapa con construcción fluida."""

    mapa = Map(
        figsize=(10, 10),
        extent=[-80, -70, -20, -10],
        fmt_scale=1.0,
        n_xticks=10,
    )

    # Construir paso a paso
    mapa.add_features(color="gray", linewidth=0.5)
    mapa.add_sat_img(zoom=6, alpha=0.7)

    # Añadir datos
    lons = [-75.5, -76.2, -74.8]
    lats = [-12.0, -13.5, -11.5]
    mapa.add_scatter(
        lon=lons,
        lat=lats,
        s=100,
        facecolor="red",
        edgecolor="black",
        marker="o",
        label="Estaciones",
    )

    # mapa.add_legend()
    mapa.add_gridlines(alpha=0.3)

    mapa.save_plot("dev/outputs/map_fluent", formats=["png"])
    print("Map con creado")


# ============================================================================
# EJEMPLO 5: Map con Inset
# ============================================================================


def example_map_with_inset():
    """Ejemplo de mapa con recuadro de zoom."""

    mapa = Map(figsize=(14, 16), extent=[-82, -68, -18, -0], fmt_scale=1.2)

    # Construcción del mapa
    mapa.add_features(color="darkgray", linewidth=0.8)
    mapa.add_sat_img(zoom=5, alpha=0.6)

    # Estaciones
    lons_all = [-77.05, -75.5, -76.2, -74.8, -71.5, -79.0, -78.5]
    lats_all = [-12.05, -12.0, -13.5, -11.5, -16.4, -8.1, -9.0]

    mapa.add_scatter(
        lon=lons_all,
        lat=lats_all,
        s=80,
        facecolor="red",
        edgecolor="darkred",
        marker="^",
        label="Estaciones Sísmicas",
        linewidths=1.5,
    )

    # Lima
    mapa.add_scatter(
        lon=-77.05,
        lat=-12.05,
        s=200,
        facecolor="yellow",
        edgecolor="black",
        marker="*",
        label="Lima",
        linewidths=2,
        zorder=10,
    )

    # mapa.add_legend()
    mapa.add_gridlines(alpha=0.4, color="white")

    # INSET: Zoom en Lima
    mapa.add_inset_axes(
        bounds=[0.6, 0.15, 0.35, 0.35],
        xlim=[-77.5, -76.5],
        ylim=[-12.5, -11.5],
        zoom_in=9,
        att_in=3,
        boundcolor="yellow",
    )

    mapa.save_plot("dev/outputs/map_with_inset", formats=["png"])
    print("Map con inset creado")


# ============================================================================
# EJEMPLO 6: Context Manager
# ============================================================================


def example_context_manager():
    """Ejemplo usando context manager para limpieza automática."""

    df = pd.DataFrame(
        {"x": [10, 20], "y": [0.1, 0.2], "z": [5, 7], "epsilon": [0.5, 1.0]}
    )

    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    # Context manager - auto cleanup
    with BarChart3D(df, key_dict, fmt_scale=1.5) as chart:
        chart.add_bars(colormap_name="coolwarm")
        chart.add_colorbar()
        chart.set_labels("X", "Y", "Z")
        chart.set_limits()
        chart.save_plot("dev/outputs/context_example", formats=["png"])

    print("Context manager completado")


# ============================================================================
# EJEMPLO 7: Comparación - Antiguo vs Nuevo
# ============================================================================


def example_comparison():
    """Comparación entre la API antigua y nueva."""

    df = pd.DataFrame(
        {
            "x": [10, 20, 30],
            "y": [0.1, 0.2, 0.3],
            "z": [5, 7, 6],
            "epsilon": [0.5, 1.0, 1.5],
        }
    )

    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    chart = BarChart3D(df, key_dict, figsize=(10, 8))
    chart.add_bars(colormap_name="viridis")
    chart.add_colorbar()
    chart.set_labels("X Axis", "Y Axis", "Z Axis")
    chart.set_limits()
    chart.save_plot("dev/outputs/comparison_new_api", formats=["png"])

    print("\nEjemplo de comparación creado")


# ============================================================================
# EJEMPLO 8: Multiple Views del mismo gráfico
# ============================================================================


def example_multiple_views():
    """Crea múltiples vistas del mismo dataset 3D."""

    df = pd.DataFrame(
        {
            "x": [10, 10, 20, 20, 30, 30, 40, 40],
            "y": [0.1, 0.2, 0.1, 0.2, 0.1, 0.2, 0.1, 0.2],
            "z": [5, 3, 7, 4, 6, 2, 8, 5],
            "epsilon": [0.5, 1.0, 0.5, 1.0, 0.5, 1.0, 0.5, 1.0],
        }
    )

    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    # Vista 1: Frontal
    chart1 = BarChart3D(df, key_dict, figsize=(12, 10))
    chart1.add_bars(colormap_name="viridis")
    chart1.add_colorbar()
    chart1.set_labels("Distancia", "Profundidad", "Magnitud")
    chart1.set_limits()
    chart1.set_view(elev=20, azim=45)
    chart1.add_text(text="Vista Frontal", position={"x": 0.02, "y": 0.95})
    chart1.save_plot("dev/outputs/view_frontal", formats=["png"])
    chart1.close()

    # Vista 2: Superior
    chart2 = BarChart3D(df, key_dict, figsize=(12, 10))
    chart2.add_bars(colormap_name="viridis")
    chart2.add_colorbar()
    chart2.set_labels("Distancia", "Profundidad", "Magnitud")
    chart2.set_limits()
    chart2.set_view(elev=90, azim=0)  # Vista desde arriba
    chart2.add_text(text="Vista Superior", position={"x": 0.02, "y": 0.95})
    chart2.save_plot("dev/outputs/view_superior", formats=["png"])
    chart2.close()

    # Vista 3: Lateral
    chart3 = BarChart3D(df, key_dict, figsize=(12, 10))
    chart3.add_bars(colormap_name="viridis")
    chart3.add_colorbar()
    chart3.set_labels("Distancia", "Profundidad", "Magnitud")
    chart3.set_limits()
    chart3.set_view(elev=0, azim=0)  # Vista lateral
    chart3.add_text(text="Vista Lateral", position={"x": 0.02, "y": 0.95})
    chart3.save_plot("dev/outputs/view_lateral", formats=["png"])
    chart3.close()

    print("Múltiples vistas creadas: frontal, superior, lateral")


# ============================================================================
# EJEMPLO 9: Construcción Incremental
# ============================================================================


def example_incremental_construction():
    """Ejemplo de construcción incremental del gráfico."""

    df = pd.DataFrame(
        {
            "x": [10, 20, 30],
            "y": [0.1, 0.2, 0.3],
            "z": [5, 7, 6],
            "epsilon": [0.5, 1.0, 1.5],
        }
    )

    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    # Crear base
    chart = BarChart3D(df, key_dict)

    print("  1. Añadiendo barras...")
    chart.add_bars(colormap_name="magma", alpha=0.9)

    print("  2. Añadiendo colorbar...")
    chart.add_colorbar(label="Valor ε")

    print("  3. Configurando etiquetas...")
    chart.set_labels("Eje X", "Eje Y", "Eje Z")

    print("  4. Ajustando límites...")
    chart.set_limits(invert_x=True)

    print("  5. Configurando vista...")
    chart.set_view(elev=30, azim=50)

    print("  6. Añadiendo anotación...")
    chart.add_text(text="Gráfico\nIncremental", position={"x": 0.85, "y": 0.85})

    print("  7. Guardando...")
    chart.save_plot("dev/outputs/incremental", formats=["png"])

    print("Construcción incremental completada")


# ============================================================================
# EJEMPLO 10: Sin PlotConfig vs Con PlotConfig
# ============================================================================


def example_with_without_config():
    """Compara gráficos con y sin PlotConfig."""

    df = pd.DataFrame(
        {
            "x": [10, 20, 30],
            "y": [0.1, 0.2, 0.3],
            "z": [5, 7, 6],
            "epsilon": [0.5, 1.0, 1.5],
        }
    )

    key_dict = {"x": "x", "y": "y", "z": "z", "color": "epsilon"}

    # SIN PlotConfig
    chart1 = BarChart3D(df, key_dict, figsize=(10, 8))
    chart1.add_bars()
    chart1.add_colorbar()
    chart1.set_labels("X", "Y", "Z")
    chart1.set_limits()
    chart1.save_plot("dev/outputs/without_config", formats=["png"])
    chart1.close()

    # CON PlotConfig
    chart2 = BarChart3D(
        df, key_dict, figsize=(10, 8), fmt_scale=1.5, n_xticks=4, n_yticks=4
    )
    chart2.add_bars()
    chart2.add_colorbar()
    chart2.set_labels("X", "Y", "Z")
    chart2.set_limits()
    chart2.save_plot("dev/outputs/with_config", formats=["png"])
    chart2.close()

    print("Comparación sin/con PlotConfig creada")


def mapa_peru_estaciones():
    """Mapa del Perú con estaciones acelerográficas RSICA y RSAQP, con insets de zoom (Ica arriba, Arequipa abajo)."""

    ruta_txt = r"C:\Users\joel.alarcon\Documents\Proyectos\AUDAS\comparacion-sencico\estaciones_igp.txt"

    # ===== Leer archivo TXT =====
    df = pd.read_csv(ruta_txt, sep=";", encoding="utf-8")

    # ===== Mapa principal =====
    mapa = Map(figsize=(7, 8), extent=[-82, -68, -18, -0], fmt_scale=1.0)
    mapa.add_features(color="darkgray", linewidth=0.8)
    mapa.add_sat_img(zoom=6, alpha=1.0)
    mapa.add_gridlines(alpha=0.4, color="white")

    # ===== Estaciones acelerográficas =====
    colores = ["blue"]

    for i, row in df.iterrows():
        mapa.add_scatter(
            lon=row["Longitud"],
            lat=row["Latitud"],
            s=50,
            facecolor=colores[i % len(colores)],
            edgecolor=None,
            marker="^",
            linewidths=1.5,
            zorder=10,
        )

    mapa.add_legend()

    # =======================================================
    # Guardar el resultado
    # =======================================================
    mapa.save_plot("dev/outputs/mapa_peru_estaciones_inset", formats=["svg"])
    print(f"Mapa del Perú con {len(df)} estaciones creado desde {ruta_txt}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EJECUTANDO EJEMPLOS - API FLUIDA")
    print("=" * 60)

    mapa_peru_estaciones()

    # Ejemplos básicos
    # print("\n[1/10] Ejemplo básico...")
    # example_barchart_fluent_api()

    # print("\n[2/10] Ejemplo mínimo...")
    # example_barchart_minimal()

    # print("\n[3/10] Ejemplo avanzado...")
    # example_barchart_advanced()

    # print("\n[4/10] Map...")
    # example_map_fluent_api()

    # print("\n[5/10] Map con inset...")
    # example_map_with_inset()

    # print("\n[6/10] Context manager...")
    # example_context_manager()

    # print("\n[7/10] Comparación de APIs...")
    # example_comparison()

    # print("\n[8/10] Múltiples vistas...")
    # example_multiple_views()

    # print("\n[9/10] Construcción incremental...")
    # example_incremental_construction()

    # print("\n[10/10] Con/sin PlotConfig...")
    # example_with_without_config()
