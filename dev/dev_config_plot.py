import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime, timedelta

from libs.config.config_plot import PlotConfig, PlotType, LegendPosition, setup_plot


def test_timeseries():
    """Prueba gráfico de series temporales con auto-aplicación."""
    print("Generando gráfico de series temporales...")

    # Genera datos de ejemplo
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(365)]
    values1 = np.cumsum(np.random.randn(365)) + 100
    values2 = np.cumsum(np.random.randn(365)) + 110
    values3 = np.cumsum(np.random.randn(365)) + 95

    # NUEVO USO: Configurar y registrar en una línea
    config = PlotConfig(
        plot_type=PlotType.TIMESERIES, dates=dates, n_xticks=5, scale=1.0
    )

    # Crea el gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    config.register(ax)  # Registra el eje para auto-aplicación

    ax.plot(dates, values1, label="Serie 1", linewidth=1.5)
    ax.plot(dates, values2, label="Serie 2", linewidth=1.5)
    ax.plot(dates, values3, label="Serie 3", linewidth=1.5)

    ax.set_title("Ejemplo de Serie Temporal")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Valor")
    ax.legend()  # Solo crear la leyenda, se aplica automáticamente

    # Se aplica todo automáticamente al guardar
    plt.savefig("dev/outputs/test_timeseries.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✓ Guardado: test_timeseries.png")


def test_timeseries_legend_variations():
    """Prueba series temporales con diferentes posiciones de leyenda."""
    print("\nGenerando series temporales con variaciones de leyenda...")

    # Genera datos de ejemplo
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(180)]
    values1 = np.cumsum(np.random.randn(180)) + 100
    values2 = np.cumsum(np.random.randn(180)) + 110

    legend_positions = [
        (LegendPosition.UPPER_LEFT, "upper_left"),
        (LegendPosition.LOWER_RIGHT, "lower_right"),
        (LegendPosition.OUTSIDE_RIGHT, "outside_right"),
        (LegendPosition.OUTSIDE_TOP, "outside_top"),
    ]

    for legend_pos, filename_suffix in legend_positions:
        # NUEVO USO: Todo en la inicialización
        config = PlotConfig(
            plot_type=PlotType.TIMESERIES,
            dates=dates,
            n_xticks=5,
            legend_position=legend_pos,
        )

        fig, ax = plt.subplots(figsize=(10, 6))
        config.register(ax)

        ax.plot(dates, values1, label="Serie A", linewidth=1.5)
        ax.plot(dates, values2, label="Serie B", linewidth=1.5)

        ax.set_title(f"Serie Temporal - Leyenda {filename_suffix}")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Valor")
        ax.legend()

        # Auto-aplicación al guardar
        plt.savefig(
            f"dev/outputs/test_timeseries_{filename_suffix}.png",
            dpi=150,
            bbox_inches="tight",
        )
        plt.close()
        print(f"✓ Guardado: test_timeseries_{filename_suffix}.png")


def test_map():
    """Prueba gráfico de mapa."""
    print("\nGenerando gráfico de mapa...")

    # NUEVO USO: Configuración simple
    config = PlotConfig(plot_type=PlotType.MAP, scale=1.0)

    # Genera datos de ejemplo (mapa simple con regiones)
    fig, ax = plt.subplots(figsize=(10, 8))
    config.register(ax)

    # Simula regiones de un mapa
    np.random.seed(42)
    x = np.random.rand(100) * 10
    y = np.random.rand(100) * 10
    colors = np.random.rand(100)
    sizes = np.random.rand(100) * 500 + 50

    scatter = ax.scatter(
        x,
        y,
        c=colors,
        s=sizes,
        alpha=0.6,
        cmap="viridis",
        edgecolors="black",
        linewidth=0.5,
    )

    # Añade algunas regiones rectangulares
    from matplotlib.patches import Rectangle

    rect1 = Rectangle(
        (1, 1), 3, 2, linewidth=2, edgecolor="red", facecolor="none", label="Región A"
    )
    rect2 = Rectangle(
        (5, 6),
        2.5,
        3,
        linewidth=2,
        edgecolor="blue",
        facecolor="none",
        label="Región B",
    )
    rect3 = Rectangle(
        (7, 2),
        2,
        2.5,
        linewidth=2,
        edgecolor="green",
        facecolor="none",
        label="Región C",
    )

    ax.add_patch(rect1)
    ax.add_patch(rect2)
    ax.add_patch(rect3)

    ax.set_title("Ejemplo de Mapa con Regiones")
    ax.legend()

    # Añade colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Intensidad")

    plt.savefig("dev/outputs/test_map_default.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✓ Guardado: test_map_default.png")


def test_map_legend_inside():
    """Prueba gráfico de mapa con leyenda dentro."""
    print("Generando gráfico de mapa con leyenda dentro...")

    config = PlotConfig(
        plot_type=PlotType.MAP, legend_position=LegendPosition.UPPER_LEFT, scale=1.0
    )

    # Genera datos de ejemplo
    fig, ax = plt.subplots(figsize=(10, 8))
    config.register(ax)

    np.random.seed(123)
    x = np.random.rand(80) * 10
    y = np.random.rand(80) * 10
    colors = np.random.rand(80)
    sizes = np.random.rand(80) * 400 + 50

    scatter = ax.scatter(
        x,
        y,
        c=colors,
        s=sizes,
        alpha=0.6,
        cmap="plasma",
        edgecolors="black",
        linewidth=0.5,
    )

    # Añade líneas de contorno
    x_grid = np.linspace(0, 10, 100)
    y_grid = np.linspace(0, 10, 100)
    X, Y = np.meshgrid(x_grid, y_grid)
    Z = np.sin(X) * np.cos(Y)

    contours = ax.contour(X, Y, Z, levels=5, colors="black", alpha=0.3, linewidths=1)
    ax.clabel(contours, inline=True, fontsize=8)

    # Añade etiquetas para la leyenda
    ax.plot([], [], "o", color="red", markersize=10, label="Punto de interés")
    ax.plot([], [], "o", color="blue", markersize=10, label="Zona monitoreada")

    ax.set_title("Mapa con Leyenda Dentro")
    ax.legend()

    plt.savefig("dev/outputs/test_map_legend_inside.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✓ Guardado: test_map_legend_inside.png")


def test_map_with_ticks():
    """Prueba gráfico de mapa con ticks y coordenadas."""
    print("Generando gráfico de mapa con ticks...")

    # NUEVO USO: Mapa con ticks usando tipo STANDARD
    config = PlotConfig(
        plot_type=PlotType.STANDARD,
        n_xticks=6,
        n_yticks=6,
        legend_position=LegendPosition.OUTSIDE_RIGHT,
        scale=1.0,
    )

    # Genera datos de ejemplo simulando coordenadas geográficas
    fig, ax = plt.subplots(figsize=(12, 8))
    config.register(ax)

    # Simula datos de temperatura en coordenadas lat/lon
    np.random.seed(456)
    lon = np.random.uniform(-80, -70, 150)
    lat = np.random.uniform(-15, -5, 150)
    temperature = np.random.uniform(15, 30, 150)
    sizes = np.random.rand(150) * 300 + 50

    scatter = ax.scatter(
        lon,
        lat,
        c=temperature,
        s=sizes,
        alpha=0.7,
        cmap="RdYlBu_r",
        edgecolors="black",
        linewidth=0.5,
    )

    # Añade contornos de temperatura
    lon_grid = np.linspace(-80, -70, 50)
    lat_grid = np.linspace(-15, -5, 50)
    LON, LAT = np.meshgrid(lon_grid, lat_grid)
    TEMP = 22 + 3 * np.sin(LON / 5) * np.cos(LAT / 3)

    contours = ax.contour(
        LON, LAT, TEMP, levels=8, colors="black", alpha=0.4, linewidths=1.5
    )
    ax.clabel(contours, inline=True, fontsize=9, fmt="%.1f°C")

    # Añade regiones de interés
    from matplotlib.patches import Rectangle

    rect1 = Rectangle(
        (-78, -12),
        3,
        3,
        linewidth=2.5,
        edgecolor="red",
        facecolor="none",
        label="Zona A",
    )
    rect2 = Rectangle(
        (-74, -8),
        2,
        2.5,
        linewidth=2.5,
        edgecolor="green",
        facecolor="none",
        label="Zona B",
    )

    ax.add_patch(rect1)
    ax.add_patch(rect2)

    ax.set_title("Mapa de Temperatura con Coordenadas")
    ax.set_xlabel("Longitud (°)")
    ax.set_ylabel("Latitud (°)")
    ax.legend()

    # Añade colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Temperatura (°C)")

    # Añade grilla para mejor legibilidad
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    plt.savefig("dev/outputs/test_map_with_ticks.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✓ Guardado: test_map_with_ticks.png")


def test_standard():
    """Prueba gráfico estándar."""
    print("\nGenerando gráfico estándar...")

    # NUEVO USO: Con rotación de etiquetas Y
    config = PlotConfig(
        plot_type=PlotType.STANDARD,
        n_xticks=6,
        n_yticks=8,
        rotate_yticks=90,  # Rotación automática
        scale=1.0,
    )

    # Genera datos de ejemplo
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x) * 10 + 50
    y2 = np.cos(x) * 8 + 45
    y3 = np.sin(x * 2) * 5 + 48

    fig, ax = plt.subplots(figsize=(10, 6))
    config.register(ax)

    ax.plot(
        x, y1, label="Función 1", linewidth=2, marker="o", markevery=10, markersize=5
    )
    ax.plot(
        x, y2, label="Función 2", linewidth=2, marker="s", markevery=10, markersize=5
    )
    ax.plot(
        x, y3, label="Función 3", linewidth=2, marker="^", markevery=10, markersize=5
    )

    ax.set_title("Ejemplo de Gráfico Estándar")
    ax.set_xlabel("Eje X")
    ax.set_ylabel("Eje Y")
    ax.legend()

    # Todo se aplica automáticamente al guardar
    plt.savefig("dev/outputs/test_standard.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✓ Guardado: test_standard.png")


def test_standard_variations():
    """Prueba gráficos estándar con variaciones."""
    print("\nGenerando gráficos estándar con variaciones...")

    # Test con diferentes escalas
    scales = [0.8, 1.0, 1.2]

    for scale in scales:
        config = PlotConfig(
            plot_type=PlotType.STANDARD,
            n_xticks=5,
            n_yticks=6,
            rotate_yticks=90,
            scale=scale,
        )

        x = np.linspace(0, 5, 50)
        y = x**2

        fig, ax = plt.subplots(figsize=(8, 6))
        config.register(ax)

        ax.plot(x, y, label=f"y = x²", linewidth=2, color="purple")
        ax.fill_between(x, 0, y, alpha=0.3, color="purple")

        ax.set_title(f"Gráfico con Escala {scale}")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.legend()

        plt.savefig(
            f"dev/outputs/test_standard_scale_{scale}.png",
            dpi=150,
            bbox_inches="tight",
        )
        plt.close()
        print(f"✓ Guardado: test_standard_scale_{scale}.png")


def test_subplots():
    """Prueba múltiples subplots con diferentes tipos."""
    print("\nGenerando gráfico con múltiples subplots...")

    # Configuración para series temporales
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(90)]

    config_ts = PlotConfig(plot_type=PlotType.TIMESERIES, dates=dates, n_xticks=4)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Comparación de Diferentes Tipos de Gráficos", fontsize=14, fontweight="bold"
    )

    # Subplot 1: Serie temporal
    config_ts.register(axes[0, 0])
    values = np.cumsum(np.random.randn(90)) + 100
    axes[0, 0].plot(dates, values, linewidth=2, color="blue")
    axes[0, 0].set_title("Serie Temporal")
    axes[0, 0].set_xlabel("Fecha")
    axes[0, 0].set_ylabel("Valor")

    # Subplot 2: Scatter
    x = np.random.randn(50) * 10 + 50
    y = np.random.randn(50) * 10 + 50
    axes[0, 1].scatter(x, y, alpha=0.6, s=100, c=y, cmap="coolwarm")
    axes[0, 1].set_title("Gráfico de Dispersión")
    axes[0, 1].set_xlabel("Variable X")
    axes[0, 1].set_ylabel("Variable Y")
    axes[0, 1].grid(True, alpha=0.3)

    # Subplot 3: Bar chart
    categories = ["A", "B", "C", "D", "E"]
    values = [23, 45, 56, 78, 32]
    axes[1, 0].bar(categories, values, color="green", alpha=0.7)
    axes[1, 0].set_title("Gráfico de Barras")
    axes[1, 0].set_xlabel("Categorías")
    axes[1, 0].set_ylabel("Frecuencia")
    axes[1, 0].grid(True, alpha=0.3, axis="y")

    # Subplot 4: Heatmap
    data = np.random.rand(10, 10)
    im = axes[1, 1].imshow(data, cmap="viridis", aspect="auto")
    axes[1, 1].set_title("Mapa de Calor")
    axes[1, 1].set_xlabel("Columna")
    axes[1, 1].set_ylabel("Fila")
    plt.colorbar(im, ax=axes[1, 1])

    plt.tight_layout()
    plt.savefig("dev/outputs/test_subplots.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✓ Guardado: test_subplots.png")


def test_context_manager():
    """Prueba usando PlotConfig como context manager."""
    print("\nGenerando gráfico con context manager...")

    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(120)]
    values = np.cumsum(np.random.randn(120)) + 50

    # NUEVO USO: Como context manager
    with PlotConfig(
        plot_type=PlotType.TIMESERIES,
        dates=dates,
        n_xticks=5,
        legend_position=LegendPosition.OUTSIDE_RIGHT,
    ) as config:
        fig, ax = plt.subplots(figsize=(10, 6))
        config.register(ax)

        ax.plot(dates, values, linewidth=2, color="darkblue", label="Serie Principal")
        ax.plot(
            dates,
            values * 1.1,
            linewidth=1.5,
            color="lightblue",
            linestyle="--",
            label="Serie +10%",
        )

        ax.set_title("Ejemplo con Context Manager")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Valor")
        ax.legend()

        plt.savefig(
            "dev/outputs/test_context_manager.png", dpi=150, bbox_inches="tight"
        )
        plt.close()
        print("✓ Guardado: test_context_manager.png")


def test_setup_plot_function():
    """Prueba la función de conveniencia setup_plot."""
    print("\nGenerando gráfico con función setup_plot...")

    x = np.linspace(0, 2 * np.pi, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)

    # NUEVO USO: Función de conveniencia
    config = setup_plot(
        plot_type=PlotType.STANDARD,
        n_xticks=7,
        n_yticks=6,
        legend_position=LegendPosition.LOWER_LEFT,
        rotate_yticks=0,  # Sin rotación
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    config.register(ax)

    ax.plot(x, y1, label="sin(x)", linewidth=2)
    ax.plot(x, y2, label="cos(x)", linewidth=2)
    ax.axhline(y=0, color="k", linestyle="-", linewidth=0.5, alpha=0.3)
    ax.axvline(x=np.pi, color="k", linestyle="-", linewidth=0.5, alpha=0.3)

    ax.set_title("Funciones Trigonométricas")
    ax.set_xlabel("x (radianes)")
    ax.set_ylabel("y")
    ax.legend()

    plt.savefig("dev/outputs/test_setup_function.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("✓ Guardado: test_setup_function.png")


def main():
    print("=" * 60)
    print("INICIANDO PRUEBAS DE CONFIGURACIÓN DE GRÁFICOS")
    print("=" * 60)

    # Pruebas de series temporales
    test_timeseries()
    test_timeseries_legend_variations()

    # Pruebas de mapas
    test_map()
    test_map_legend_inside()
    test_map_with_ticks()

    # Pruebas de gráficos estándar
    test_standard()
    test_standard_variations()

    # Pruebas de subplots
    test_subplots()

    # Pruebas de nuevas características
    test_context_manager()
    test_setup_plot_function()


if __name__ == "__main__":
    main()
