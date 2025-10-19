import matplotlib.pyplot as plt

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from libs.config.config_plot import PlotConfig

from libs.helpers.storage_helpers import validate_file

from libs.config.config_logger import get_logger

logger = get_logger()


class BasePlotter(ABC):
    """
    Clase base abstracta para diferentes tipos de plotters.

    Proporciona funcionalidad común para crear, configurar y guardar gráficos.
    Compatible con PlotConfig para configuración avanzada de matplotlib.
    """

    def __init__(
        self,
        figsize: tuple = (10, 10),
        **kwargs,
    ):
        """
        Inicializa el plotter base.

        Args:
            figsize (tuple): Tamaño de la figura (ancho, alto).
            plot_config (PlotConfig, optional): Configuración de matplotlib.
            **kwargs: Argumentos adicionales específicos del plotter.
        """
        self.figsize = figsize
        self.fig = None
        self.ax = None
        self._initialize_plot(**kwargs)

        # Si hay PlotConfig, registrar el eje automáticamente
        if self.plot_config and self.ax is not None:
            self.plot_config.register(self.ax)

    @abstractmethod
    def _initialize_plot(self, **kwargs):
        """
        Inicializa la figura y los ejes.
        Debe ser implementado por las subclases.
        """
        pass

    def close(self):
        """Cierra la figura."""
        if self.fig is not None:
            plt.close(self.fig)

    def save_plot(
        self,
        filename: str,
        formats: List[str],
        dpi: int = 600,
        **kwargs,
    ):
        """
        Guarda el gráfico en los formatos especificados.

        Args:
            filename (str): Nombre base del archivo sin extensión.
            formats (List[str]): Lista de formatos para guardar ('png', 'svg', 'pdf', etc.).
            dpi (int): Resolución en puntos por pulgada.
            **kwargs: Argumentos adicionales para plt.savefig().

        Note:
            Si usa PlotConfig, la configuración se aplica automáticamente.
        """

        for fmt in formats:
            fpath = f"{filename}.{fmt}"
            validate_file(fpath, create_parents=True)
            self.fig.savefig(fpath, format=fmt, dpi=dpi, **kwargs)

            logger.info(f"Gráfico guardado: {fpath}")

    def set_title(self, title: str, **kwargs):
        """
        Establece el título del gráfico.

        Args:
            title (str): Título del gráfico.
            **kwargs: Argumentos adicionales para set_title().
        """
        if self.ax is not None:
            self.ax.set_title(title, **kwargs)

    def add_text(
        self,
        text: str,
        position: Dict[str, float],
        fontsize: int = 12,
        color: str = "black",
        ha: str = "left",
        va: str = "center",
        bbox_props: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Añade texto a la figura.

        Args:
            text (str): El texto a mostrar.
            position (Dict[str, float]): Posición con claves 'x' y 'y' (coordenadas normalizadas).
            fontsize (int): Tamaño de la fuente.
            color (str): Color del texto.
            ha (str): Alineación horizontal.
            va (str): Alineación vertical.
            bbox_props (Dict[str, Any]): Propiedades del cuadro contenedor.
            **kwargs: Argumentos adicionales para fig.text().
        """
        self.fig.text(
            position["x"],
            position["y"],
            text,
            fontsize=fontsize,
            color=color,
            ha=ha,
            va=va,
            bbox=bbox_props,
            **kwargs,
        )

    def get_figure(self):
        """Retorna la figura de matplotlib."""
        return self.fig

    def get_axes(self):
        """Retorna los ejes del gráfico."""
        return self.ax

    def get_config(self) -> Optional[PlotConfig]:
        """Retorna la configuración de PlotConfig si existe."""
        return self.plot_config

    def set_config(self, plot_config: PlotConfig):
        """
        Establece o actualiza la configuración de PlotConfig.

        Args:
            plot_config (PlotConfig): Nueva configuración.
        """
        self.plot_config = plot_config
        if self.ax is not None:
            self.plot_config.register(self.ax)

    def __enter__(self):
        """Permite usar el plotter como context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la figura al salir del contexto."""
        self.close()
