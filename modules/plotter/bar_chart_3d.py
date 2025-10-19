import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from modules.plotter.base_plotter import BasePlotter
from libs.config.config_plot import PlotConfig, PlotType, LegendPosition


class BarChart3D(BasePlotter):
    def __init__(
        self,
        df: pd.DataFrame,
        key_dict: dict,
        dx: float = 5,
        dy: float = 0.05,
        **kwargs,
    ):
        """
        Inicializa la clase BarChart3D.

        Args:
            df (pd.DataFrame): DataFrame con las columnas necesarias.
            key_dict (dict): Diccionario con claves para X, Y, Z y COLOR.
            dx (float): Ancho de las barras en el eje X.
            dy (float): Ancho de las barras en el eje Y.
        """
        self.df = df
        self.key_dict = key_dict
        self.dx = dx
        self.dy = dy

        self.color_map = None

        super().__init__(**kwargs)

    def _initialize_plot(self, **kwargs):
        """Inicializa la figura con proyección 3D."""
        self.fig = plt.figure(figsize=self.figsize)
        self.ax = self.fig.add_subplot(111, projection="3d")

        self.plot_config = PlotConfig(
            plot_type=PlotType.STANDARD,
            legend_position=LegendPosition.UPPER_RIGHT,
            **kwargs,
        )
        self.plot_config.register(self.ax)

    def create_color_map(self, colormap_name: str = "viridis") -> dict:
        """
        Crea un mapa de colores para los valores únicos.

        Args:
            colormap_name (str): Nombre del colormap a utilizar.

        Returns:
            dict: Mapa de colores.
        """
        eps_values = np.sort(self.df[self.key_dict["color"]].unique())
        colors = plt.colormaps[colormap_name](np.linspace(0, 1, len(eps_values)))
        return dict(zip(eps_values, colors))

    def add_bars(
        self,
        colormap_name: str = "viridis",
        alpha: float = 1,
        edgecolor: str = "black",
        **kwargs,
    ):
        """
        Añade las barras 3D apiladas al gráfico.

        Args:
            colormap_name (str): Nombre del colormap a utilizar.
            alpha (float): Transparencia de las barras.
            edgecolor (str): Color del borde de las barras.
            **kwargs: Argumentos adicionales para bar3d.
        """
        # Crear mapa de colores si no existe
        if self.color_map is None:
            self.color_map = self.create_color_map(colormap_name)

        grouped = self.df.groupby(
            [self.key_dict["x"], self.key_dict["y"], self.key_dict["color"]],
            as_index=False,
        ).sum()

        eps_values = np.sort(self.df[self.key_dict["color"]].unique())

        for (x_, y_), group in grouped.groupby(
            [self.key_dict["x"], self.key_dict["y"]]
        ):
            z_pos = 0

            for eps_val in eps_values:
                mask = group[self.key_dict["color"]] == eps_val
                z_filtered = group[self.key_dict["z"]][mask]

                if not z_filtered.empty:
                    dz = z_filtered.values[0]
                    color = self.color_map[eps_val]

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

                    z_pos += dz

    def add_colorbar(self, label: str = "epsilon (ε)", **kwargs):
        """
        Añade una barra de colores al gráfico.

        Args:
            label (str): Etiqueta de la barra de colores.
            **kwargs: Argumentos adicionales para colorbar.
        """
        if self.color_map is None:
            raise ValueError("Debe llamar a add_bars() antes de add_colorbar()")

        cmap = mpl.colors.ListedColormap(
            [self.color_map[eps_val] for eps_val in self.color_map.keys()]
        )
        bounds = np.append(
            list(self.color_map.keys()), list(self.color_map.keys())[-1] + 1
        )
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
            label,
            ha="center",
            va="center",
            color="black",
            fontsize=12,
            transform=cbar.ax.transAxes,
            rotation=90,
        )

    def set_labels(self, x_label: str, y_label: str, z_label: str):
        """
        Configura las etiquetas de los ejes.

        Args:
            x_label (str): Etiqueta del eje X.
            y_label (str): Etiqueta del eje Y.
            z_label (str): Etiqueta del eje Z.
        """
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_zlabel(z_label)

    def set_limits(self, invert_x: bool = True):
        """
        Establece los límites de los ejes.

        Args:
            invert_x (bool): Si True, invierte el eje X.
        """
        max_x = np.ceil(self.df[self.key_dict["x"]].max())
        max_y = np.ceil(self.df[self.key_dict["y"]].max())

        self.ax.set_xlim([min(self.df[self.key_dict["x"]]), max_x])
        self.ax.set_ylim([min(self.df[self.key_dict["y"]]), max_y])

        if invert_x:
            self.ax.invert_xaxis()

    def set_view(self, elev: float = None, azim: float = None):
        """
        Configura el ángulo de vista del gráfico 3D.

        Args:
            elev (float): Elevación (ángulo vertical en grados).
            azim (float): Azimut (ángulo horizontal en grados).
        """
        self.ax.view_init(elev=elev, azim=azim)
