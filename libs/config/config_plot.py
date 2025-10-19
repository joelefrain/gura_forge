import functools

import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from typing import Optional, List

from libs.config.config_variables import DEFAULT_FONT, DATE_FORMAT

from libs.config.config_logger import get_logger

logger = get_logger()


class PlotType:
    """Clase tipo enum para tipos de gráficos."""

    TIMESERIES = "timeseries"
    MAP = "map"
    STANDARD = "standard"


class LegendPosition:
    """Clase tipo enum para posiciones de leyenda."""

    # Posiciones dentro del gráfico
    UPPER_LEFT = "upper left"
    UPPER_RIGHT = "upper right"
    UPPER_CENTER = "upper center"
    LOWER_LEFT = "lower left"
    LOWER_RIGHT = "lower right"
    LOWER_CENTER = "lower center"
    CENTER_LEFT = "center left"
    CENTER_RIGHT = "center right"
    CENTER = "center"
    BEST = "best"

    # Posiciones fuera del gráfico (requieren configuración especial)
    OUTSIDE_RIGHT = "outside_right"
    OUTSIDE_LEFT = "outside_left"
    OUTSIDE_TOP = "outside_top"
    OUTSIDE_BOTTOM = "outside_bottom"


class PlotConfig:
    """
    Clase para configurar y gestionar automáticamente parámetros de matplotlib.

    Uso:
        config = PlotConfig(
            plot_type=PlotType.TIMESERIES,
            dates=my_dates,  # para timeseries
            n_xticks=5,
            n_yticks=6,
            legend_position=LegendPosition.OUTSIDE_RIGHT,
            rotate_yticks=90
        )

        fig, ax = plt.subplots()
        config.register(ax)  # Registra el eje para auto-aplicación

        # ... crear gráfico ...
        ax.legend()

        plt.savefig("output.png")  # Se aplica automáticamente la configuración
    """

    # Variables de clase para almacenar configuraciones activas
    _active_configs = {}  # {ax_id: PlotConfig instance}
    _original_savefig = None
    _original_show = None
    _hooks_installed = False

    def __init__(
        self,
        plot_type: str = PlotType.TIMESERIES,
        dates: Optional[List] = None,
        n_xticks: int = 5,
        n_yticks: int = 5,
        ymargin: float = 0.20,
        fmt_scale: float = 1.0,
        legend_position: Optional[str] = None,
        rotate_yticks: Optional[float] = None,
        rotate_xticks: Optional[float] = None,
    ):
        """
        Inicializa la configuración del gráfico.

        Parámetros
        ----------
        plot_type : str
            Tipo de gráfico: PlotType.TIMESERIES, PlotType.MAP, o PlotType.STANDARD
        dates : list, optional
            Lista de fechas para series temporales (requerido si plot_type es TIMESERIES)
        n_xticks : int
            Número de ticks en el eje x (por defecto: 5)
        n_yticks : int
            Número de ticks en el eje y (por defecto: 5)
        ymargin : float
            Margen para el eje y (por defecto: 0.20)
        fmt_scale : float
            Factor de escala para tamaños (por defecto: 1.0)
        legend_position : str, optional
            Posición de la leyenda. Si es None, usa valores por defecto según plot_type
        rotate_yticks : float, optional
            Ángulo de rotación para etiquetas del eje Y
        rotate_xticks : float, optional
            Ángulo de rotación para etiquetas del eje X
        """
        self.plot_type = plot_type
        self.dates = dates
        self.n_xticks = n_xticks
        self.n_yticks = n_yticks
        self.ymargin = ymargin
        self.fmt_scale = fmt_scale
        self.rotate_yticks = rotate_yticks
        self.rotate_xticks = rotate_xticks

        # Determina la posición de leyenda por defecto según el tipo
        if legend_position is None:
            if plot_type == PlotType.MAP:
                legend_position = LegendPosition.OUTSIDE_RIGHT
            else:
                legend_position = LegendPosition.UPPER_LEFT

        self.legend_position = legend_position
        self._legend_config = self._get_legend_config(legend_position)

        # Validaciones
        if plot_type == PlotType.TIMESERIES and dates is None:
            logger.warning(
                "PlotType.TIMESERIES requiere el parámetro 'dates'. "
                "Asegúrate de proporcionarlo para configuración correcta de ticks."
            )

        # Aplica configuración global de matplotlib
        self._setup_matplotlib()

        # Instala hooks globales si aún no están instalados
        if not PlotConfig._hooks_installed:
            PlotConfig._install_hooks()

    def _setup_matplotlib(self):
        """Configura parámetros globales de matplotlib."""
        try:
            import locale

            locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")
        except locale.Error:
            logger.warning(
                "Warning: Unable to set locale to 'fr_FR.UTF-8'. Using default locale."
            )

        plt.rcParams["axes.formatter.use_locale"] = True
        plt.rcParams["backend"] = "Agg"
        plt.rcParams["font.family"] = DEFAULT_FONT
        plt.rcParams["font.size"] = int(8 * self.fmt_scale)

        # Configuración de figura
        plt.rcParams["figure.constrained_layout.use"] = True
        plt.rcParams["figure.constrained_layout.h_pad"] = 0
        plt.rcParams["figure.constrained_layout.hspace"] = 0
        plt.rcParams["figure.constrained_layout.w_pad"] = 0
        plt.rcParams["figure.constrained_layout.wspace"] = 0
        plt.rcParams["figure.edgecolor"] = "None"
        plt.rcParams["figure.facecolor"] = "None"
        plt.rcParams["figure.titlesize"] = int(10 * self.fmt_scale)
        plt.rcParams["figure.titleweight"] = "bold"
        plt.rcParams["figure.autolayout"] = True

        # Configuración de ejes
        plt.rcParams["axes.facecolor"] = "None"
        plt.rcParams["axes.edgecolor"] = "black"
        plt.rcParams["axes.grid"] = True
        plt.rcParams["axes.ymargin"] = self.ymargin
        plt.rcParams["axes.spines.bottom"] = True
        plt.rcParams["axes.spines.left"] = True
        plt.rcParams["axes.spines.right"] = True
        plt.rcParams["axes.spines.top"] = True
        plt.rcParams["axes.titleweight"] = "bold"
        plt.rcParams["axes.titlesize"] = int(10 * self.fmt_scale)
        plt.rcParams["axes.labelsize"] = int(9 * self.fmt_scale)
        plt.rcParams["axes.titlepad"] = int(4 * self.fmt_scale)
        plt.rcParams["axes.titlelocation"] = "center"

        # Configuración por defecto de ticks (visibles)
        plt.rcParams["xtick.labelbottom"] = True
        plt.rcParams["ytick.labelleft"] = True
        plt.rcParams["xtick.bottom"] = True
        plt.rcParams["ytick.left"] = True
        plt.rcParams["xtick.top"] = False
        plt.rcParams["ytick.right"] = False
        plt.rcParams["ytick.labelsize"] = int(8 * self.fmt_scale)
        plt.rcParams["xtick.labelsize"] = int(8 * self.fmt_scale)

        # Configuración de leyenda
        plt.rcParams["legend.fontsize"] = int(8 * self.fmt_scale)
        plt.rcParams["legend.facecolor"] = "white"
        plt.rcParams["legend.framealpha"] = 0.15
        plt.rcParams["legend.edgecolor"] = "None"
        plt.rcParams["legend.fancybox"] = False

        # Configuración de grilla
        plt.rcParams["grid.alpha"] = 0.25
        plt.rcParams["grid.color"] = "gray"
        plt.rcParams["grid.linestyle"] = "-"
        plt.rcParams["grid.linewidth"] = 0.05 * self.fmt_scale
        plt.rcParams["text.color"] = "black"

        # Aplica configuraciones específicas según el tipo
        if self.plot_type == PlotType.TIMESERIES:
            self._configure_timeseries()
        elif self.plot_type == PlotType.MAP:
            self._configure_map()
        else:  # STANDARD
            self._configure_standard()

    def _configure_timeseries(self):
        """Configura ajustes para gráficos de series temporales."""
        plt.rcParams["axes.xmargin"] = 0
        plt.rcParams["xtick.minor.visible"] = False
        plt.rcParams["ytick.minor.visible"] = True
        plt.rcParams["xtick.labelbottom"] = True
        plt.rcParams["ytick.labelleft"] = True
        plt.rcParams["xtick.bottom"] = True
        plt.rcParams["ytick.left"] = True
        plt.rcParams["date.autoformatter.day"] = DATE_FORMAT
        plt.rcParams["date.autoformatter.month"] = DATE_FORMAT
        plt.rcParams["date.autoformatter.year"] = DATE_FORMAT
        plt.rcParams["xtick.major.size"] = 4 * self.fmt_scale
        plt.rcParams["ytick.major.size"] = 4 * self.fmt_scale
        plt.rcParams["xtick.direction"] = "out"
        plt.rcParams["ytick.direction"] = "out"

    def _configure_map(self):
        """Configura ajustes para gráficos de mapas."""
        plt.rcParams["axes.xmargin"] = 0
        plt.rcParams["axes.ymargin"] = 0
        plt.rcParams["xtick.minor.visible"] = False
        plt.rcParams["ytick.minor.visible"] = False
        plt.rcParams["xtick.labelbottom"] = False
        plt.rcParams["ytick.labelleft"] = False
        plt.rcParams["xtick.bottom"] = False
        plt.rcParams["ytick.left"] = False
        plt.rcParams["axes.grid"] = False

    def _configure_standard(self):
        """Configura ajustes para gráficos estándar."""
        plt.rcParams["axes.xmargin"] = 0.05
        plt.rcParams["xtick.minor.visible"] = True
        plt.rcParams["ytick.minor.visible"] = True
        plt.rcParams["xtick.labelbottom"] = True
        plt.rcParams["ytick.labelleft"] = True
        plt.rcParams["xtick.bottom"] = True
        plt.rcParams["ytick.left"] = True
        plt.rcParams["xtick.major.size"] = 4 * self.fmt_scale
        plt.rcParams["ytick.major.size"] = 4 * self.fmt_scale
        plt.rcParams["xtick.minor.size"] = 2 * self.fmt_scale
        plt.rcParams["ytick.minor.size"] = 2 * self.fmt_scale
        plt.rcParams["xtick.direction"] = "out"
        plt.rcParams["ytick.direction"] = "out"

    @staticmethod
    def _get_legend_config(position: str) -> dict:
        """Obtiene la configuración de leyenda según la posición especificada."""
        outside_positions = {
            LegendPosition.OUTSIDE_RIGHT: {
                "loc": "center left",
                "bbox_to_anchor": (1.0, 0.5),
            },
            LegendPosition.OUTSIDE_LEFT: {
                "loc": "center right",
                "bbox_to_anchor": (-0.1, 0.5),
            },
            LegendPosition.OUTSIDE_TOP: {
                "loc": "lower center",
                "bbox_to_anchor": (0.5, 1.0),
            },
            LegendPosition.OUTSIDE_BOTTOM: {
                "loc": "upper center",
                "bbox_to_anchor": (0.5, -0.1),
            },
        }

        if position in outside_positions:
            return outside_positions[position]
        else:
            return {"loc": position}

    def register(self, ax: Axes, apply_to_secondary: bool = True) -> Axes:
        """
        Registra un eje para auto-aplicación de configuración.

        Parámetros
        ----------
        ax : matplotlib.axes.Axes
            El eje a registrar
        apply_to_secondary : bool
            Si True, también aplica configuración a ejes secundarios (twinx/twiny)
            Por defecto True para mantener consistencia visual

        Retorna
        -------
        matplotlib.axes.Axes
            El mismo eje (para encadenamiento)
        """
        ax_id = id(ax)
        PlotConfig._active_configs[ax_id] = {
            "config": self,
            "apply_to_secondary": apply_to_secondary,
            "is_primary": True,  # Marca este como eje primario
        }
        return ax

    def apply(self, ax: Axes):
        """
        Aplica manualmente la configuración a un eje.

        Parámetros
        ----------
        ax : matplotlib.axes.Axes
            El eje donde aplicar la configuración
        """
        self._apply_to_axis(ax)

    def _apply_to_axis(self, ax: Axes, is_secondary: bool = False):
        """
        Aplica todas las configuraciones a un eje específico.
        Prioridades:
        1. Ticks (más fundamental)
        2. Rotaciones de etiquetas
        3. Leyenda (más superficial)

        Parámetros
        ----------
        ax : matplotlib.axes.Axes
            El eje donde aplicar la configuración
        is_secondary : bool
            Si True, es un eje secundario (twinx/twiny) y se aplica configuración limitada
        """
        # Prioridad 1: Configurar ticks según el tipo de gráfico
        # Para ejes secundarios, no modificamos los ticks X (compartidos con el primario)
        if not is_secondary:
            if self.plot_type == PlotType.TIMESERIES and self.dates is not None:
                self._set_timeseries_ticks(ax, self.dates, self.n_xticks)
            elif self.plot_type == PlotType.STANDARD:
                self._set_standard_ticks(ax, self.n_xticks, self.n_yticks)
            # MAP no necesita configuración de ticks adicional

        # Para ejes secundarios (twinx), configurar solo ticks Y
        if is_secondary and self.plot_type == PlotType.STANDARD:
            from matplotlib.ticker import MaxNLocator

            ax.yaxis.set_major_locator(MaxNLocator(nbins=self.n_yticks))

        # Prioridad 2: Aplicar rotaciones de etiquetas
        if self.rotate_yticks is not None:
            ax.tick_params(axis="y", rotation=self.rotate_yticks)

        # Solo aplicar rotación X en eje primario
        if self.rotate_xticks is not None and not is_secondary:
            ax.tick_params(axis="x", rotation=self.rotate_xticks)

        # Prioridad 3: Configurar leyenda si existe
        # Solo en el eje primario para evitar duplicados
        if not is_secondary:
            legend = ax.get_legend()
            if legend is not None:
                ax.legend(**self._legend_config)

    def _set_timeseries_ticks(self, ax: Axes, dates: List, n_ticks: int):
        """
        Establece ticks para gráficos de series temporales.
        Garantiza que el primer y último valor siempre estén incluidos.
        """
        if len(dates) == 0:
            return

        if len(dates) == 1:
            ax.set_xticks([dates[0]])
            ax.set_xlim(dates[0], dates[0])
            return

        # Si tenemos menos puntos que ticks solicitados, usar todos los puntos
        if len(dates) <= n_ticks:
            ax.set_xticks(dates)
            ax.set_xlim(dates[0], dates[-1])
            return

        # Calcular índices distribuidos uniformemente
        # Asegurar que siempre incluimos primero y último
        step = (len(dates) - 1) / (n_ticks - 1)
        indices = [0]  # Primer elemento

        # Elementos intermedios
        for i in range(1, n_ticks - 1):
            idx = int(round(i * step))
            # Evitar duplicados
            if idx != indices[-1] and idx < len(dates) - 1:
                indices.append(idx)

        # Último elemento (siempre)
        if len(dates) - 1 not in indices:
            indices.append(len(dates) - 1)

        # Asegurar que no excedemos n_ticks
        if len(indices) > n_ticks:
            # Mantener primero y último, distribuir el resto
            indices = [0] + indices[1:-1:2] + [len(dates) - 1]
            indices = sorted(list(set(indices)))[:n_ticks]

        # Establecer los ticks
        ax.set_xticks([dates[i] for i in indices])
        ax.set_xlim(dates[0], dates[-1])

    def _set_standard_ticks(self, ax: Axes, n_xticks: int, n_yticks: int):
        """Establece ticks para gráficos estándar."""
        from matplotlib.ticker import MaxNLocator

        ax.xaxis.set_major_locator(MaxNLocator(nbins=n_xticks))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=n_yticks))

    @classmethod
    def _install_hooks(cls):
        """Instala hooks en savefig y show para auto-aplicar configuraciones."""
        if cls._hooks_installed:
            return

        # Guarda las funciones originales
        cls._original_savefig = plt.savefig
        cls._original_show = plt.show

        # Define wrapper para savefig
        @functools.wraps(cls._original_savefig)
        def savefig_wrapper(*args, **kwargs):
            cls._apply_all_configs()

            # Aplicar guardado ajustado automáticamente
            kwargs.setdefault("bbox_inches", "tight")
            kwargs.setdefault("pad_inches", 0)

            return cls._original_savefig(*args, **kwargs)

        # Define wrapper para show
        @functools.wraps(cls._original_show)
        def show_wrapper(*args, **kwargs):
            cls._apply_all_configs()
            return cls._original_show(*args, **kwargs)

        # Reemplaza las funciones
        plt.savefig = savefig_wrapper
        plt.show = show_wrapper

        cls._hooks_installed = True
        logger.debug("PlotConfig hooks instalados correctamente")

    @classmethod
    def _apply_all_configs(cls):
        """Aplica todas las configuraciones registradas antes de guardar/mostrar."""
        for ax_id, config_data in list(cls._active_configs.items()):
            config = config_data["config"]
            apply_to_secondary = config_data["apply_to_secondary"]

            # Busca el eje correspondiente en todas las figuras
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                for ax in fig.get_axes():
                    if id(ax) == ax_id:
                        # Aplica configuración al eje primario
                        config._apply_to_axis(ax, is_secondary=False)

                        # Si tiene ejes secundarios (twinx/twiny), aplícales configuración limitada
                        if apply_to_secondary:
                            # Busca ejes secundarios compartiendo el mismo patch
                            for other_ax in fig.get_axes():
                                if (
                                    other_ax is not ax
                                    and other_ax.bbox.bounds == ax.bbox.bounds
                                ):
                                    # Es un eje secundario (twinx o twiny)
                                    config._apply_to_axis(other_ax, is_secondary=True)
                        break

    @classmethod
    def clear_registry(cls):
        """Limpia el registro de configuraciones activas."""
        cls._active_configs.clear()

    @classmethod
    def uninstall_hooks(cls):
        """Desinstala los hooks (útil para testing o limpieza)."""
        if cls._hooks_installed and cls._original_savefig and cls._original_show:
            plt.savefig = cls._original_savefig
            plt.show = cls._original_show
            cls._hooks_installed = False
            logger.debug("PlotConfig hooks desinstalados")

    def __enter__(self):
        """Soporte para context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Limpia al salir del contexto."""
        # No limpiamos el registro aquí para permitir múltiples gráficos
        pass


# Función de conveniencia para uso simple
def setup_plot(plot_type: str = PlotType.TIMESERIES, **kwargs) -> PlotConfig:
    """
    Función de conveniencia para configurar rápidamente un gráfico.

    Parámetros
    ----------
    plot_type : str
        Tipo de gráfico
    **kwargs
        Parámetros adicionales para PlotConfig

    Retorna
    -------
    PlotConfig
        Instancia de configuración

    Ejemplo
    -------
    >>> config = setup_plot(
    ...     plot_type=PlotType.TIMESERIES,
    ...     dates=my_dates,
    ...     n_xticks=5
    ... )
    >>> fig, ax = plt.subplots()
    >>> config.register(ax)
    >>> ax.plot(dates, values)
    >>> plt.savefig("output.png")  # Se aplica automáticamente
    """
    return PlotConfig(plot_type=plot_type, **kwargs)
