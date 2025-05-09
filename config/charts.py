import matplotlib.pyplot as plt
import matplotlib
import locale


class PlotConfig:
    # Variables globales de matplotlib
    font_family = "Arial"
    legend_loc = "upper right"

    @classmethod
    def setup_matplotlib(cls):
        """Configura los parámetros globales de matplotlib."""
        plt.rcParams["font.family"] = cls.font_family
        plt.rcParams["legend.loc"] = cls.legend_loc
        plt.rcParams["axes.formatter.use_locale"] = True

        # Establece la configuración regional para usar coma como separador decimal
        locale.setlocale(locale.LC_ALL, "es_ES.UTF-8")

        # Establece un backend no interactivo para evitar que los gráficos se muestren
        matplotlib.use("Agg")
