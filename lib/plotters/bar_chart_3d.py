import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as patches
import matplotlib as mpl


class BarChart3D:
    def __init__(
        self,
        df: pd.DataFrame,
        key_dict: dict,
        dx: float = 5,
        dy: float = 0.05,
        figsize: tuple = (15, 15),
        facecolor="white",
    ):
        """
        Inicializa la clase BarChart3D.

        Args:
            df (pd.DataFrame): DataFrame con las columnas necesarias.
            key_dict (dict): Diccionario que contiene las claves para las columnas X, Y, Z y COLOR.
            dx (float): Ancho de las barras en el eje X.
            dy (float): Ancho de las barras en el eje Y.
            figsize (tuple): Tamaño de la figura.
        """
        self.df = df
        self.key_dict = key_dict  # Diccionario con claves para X, Y, Z y COLOR
        self.dx = dx
        self.dy = dy
        self.figsize = figsize
        self.fig = plt.figure(figsize=self.figsize)
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.facecolor = facecolor

    def create_color_map(self, colormap_name: str = "viridis") -> dict:
        """
        Crea un mapa de colores para los valores únicos de epsilon.

        Args:
            colormap_name (str): Nombre del colormap a utilizar.

        Returns:
            dict: Mapa de colores.
        """
        eps_values = np.sort(self.df[self.key_dict["color"]].unique())
        colors = plt.colormaps[colormap_name](np.linspace(0, 1, len(eps_values)))
        return dict(zip(eps_values, colors))

    def plot_bars(self, color_map: dict, alpha=1, edgecolor="black", **kwargs):
        """
        Crea las barras 3D apiladas en el gráfico.

        Args:
            color_map (dict): Mapa de colores.
        """
        # Agrupar por 'x' y 'y' y sumar las contribuciones
        grouped = self.df.groupby(
            [self.key_dict["x"], self.key_dict["y"], self.key_dict["color"]],
            as_index=False,
        ).sum()

        # Ordenar los valores de eps de menor a mayor
        eps_values = np.sort(self.df[self.key_dict["color"]].unique())

        for (x_, y_), group in grouped.groupby(
            [self.key_dict["x"], self.key_dict["y"]]
        ):
            # Inicializa la posición en el eje Z para apilar las barras
            z_pos = 0

            for eps_val in eps_values:
                # Filtra los datos para el valor actual de eps
                mask = group[self.key_dict["color"]] == eps_val
                z_filtered = group[self.key_dict["z"]][mask]

                if not z_filtered.empty:
                    dz = z_filtered.values[0]  # Tomar la contribución
                    color = color_map[eps_val]

                    # Dibuja la barra apilada
                    self.ax.bar3d(
                        x_,
                        y_,
                        z_pos,
                        self.dx,
                        self.dy,
                        dz,
                        color=color,
                        alpha=alpha,
                        edgecolor=edgecolor,
                        **kwargs,
                    )

                    # Actualiza la posición en el eje Z
                    z_pos += dz

    def add_colorbar(self, color_map: dict, **kwargs):
        """
        Añade una barra de colores al gráfico.

        Args:
            color_map (dict): Mapa de colores.
        """
        cmap = mpl.colors.ListedColormap(
            [color_map[eps_val] for eps_val in color_map.keys()]
        )
        bounds = np.append(list(color_map.keys()), list(color_map.keys())[-1] + 1)
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

        cbar = self.fig.colorbar(
            mpl.cm.ScalarMappable(cmap=cmap, norm=norm),
            ax=self.ax,
            orientation="vertical",
            pad=0.1,
            aspect=20,
            shrink=0.2,
            **kwargs,
        )
        cbar.ax.text(
            5,
            0.5,
            "epsilon (ε)",
            ha="center",
            va="center",
            color="black",
            fontsize=12,
            transform=cbar.ax.transAxes,
            rotation=90,
            **kwargs,
        )

    def add_textbox(
        self,
        text: str,
        position: dict = {"x": 0.85, "y": 0.8},
        box_size: dict = {"width": 0.5, "height": 0.5},
        **kwargs,
    ):
        """
        Añade un texto a la figura, cerca de la leyenda de color.

        Args:
            text (str): El texto que se mostrará.
            position (dict): Posición del texto con claves 'x' y 'y' (coordenadas normalizadas).
            box_size (dict): Tamaño del cuadro que contiene el texto con claves 'width' y 'height'.
        """
        pad_value = max(box_size["width"], box_size["height"])
        self.fig.text(
            position["x"],
            position["y"],
            text,
            fontsize=12,
            color="black",
            ha="left",
            va="center",  # Alineación horizontal a la izquierda, vertical centrada
            bbox=dict(
                facecolor="white",
                edgecolor="black",
                boxstyle=f"round,pad={pad_value}",
                **kwargs,
            ),
        )

    def set_labels(self, x_label, y_label, z_label):
        """Configura las etiquetas de los ejes."""
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_zlabel(z_label)

    def set_limits(self):
        """Establece los límites máximos de los ejes redondeando hacia arriba."""
        max_x = np.ceil(self.df[self.key_dict["x"]].max())
        max_y = np.ceil(self.df[self.key_dict["y"]].max())

        self.ax.set_xlim([min(self.df[self.key_dict["x"]]), max_x])
        self.ax.set_ylim([min(self.df[self.key_dict["y"]]), max_y])

        # Invertir el eje (X)
        self.ax.invert_xaxis()

    def set_background(self):
        """Configura el color de fondo de la figura y los ejes a blanco."""
        self.fig.patch.set_facecolor(self.facecolor)
        self.ax.set_facecolor(self.facecolor)

    def save_plot(self, filename: str, formats: list, dpi=600, **kwargs):
        """
        Guarda el gráfico en los formatos especificados.

        Args:
            filename (str): Nombre base del archivo sin extensión.
            formats (list): Lista de formatos para guardar ('png', 'svg').
        """
        for fmt in formats:
            full_filename = f"{filename}.{fmt}"
            plt.tight_layout()
            plt.savefig(full_filename, format=fmt, dpi=dpi, **kwargs)

    def create_plot(
        self,
        colormap_name: str = "viridis",
        x_label: str = "axis x",
        y_label: str = "axis y",
        z_label: str = "axis z",
    ):
        """
        Crea y guarda el gráfico 3D.

        Args:
            colormap_name (str): Nombre del colormap a utilizar.
            filename (str): Nombre base del archivo para guardar.
            formats (list): Lista de formatos para guardar ('png', 'svg').
            text (str): Texto a mostrar en la figura.
            position (dict): Posición del cuadro de texto con claves 'x' y 'y' (proporcional al gráfico).
            box_size (dict): Tamaño del cuadro de texto con claves 'width' y 'height'.
        """
        color_map = self.create_color_map(colormap_name)
        self.plot_bars(color_map)
        self.add_colorbar(color_map)
        self.set_labels(x_label, y_label, z_label)
        self.set_limits()
        self.set_background()
