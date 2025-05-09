import numpy as np
import pandas as pd
from lib.plotters.bar_chart_3d import BarChart3D
from lib.tools.utils import crop_image
from config.config import RETURN_PRD_LST, SEP_SYMBOL_NAME, SEP_SYMBOL_COLM, SEP_DECIMAL


class DisaggregationAnalyser:
    def __init__(
        self,
        key_dict,
        colormap_name,
        formats,
        labels,
        n_period_return,
        poe,
        spc_acc,
        df,
    ):
        """
        Inicializa la clase DisaggregationPlotter.

        Args:
            key_dict (dict): Diccionario que mapea claves a los nombres de las columnas en el dataframe.
            colormap_name (str): Nombre del colormap a utilizar para los gráficos.
            formats (list of str): Lista de formatos en los que se guardará el gráfico (ej., 'png', 'pdf').
            labels (dict): Diccionario con etiquetas para los ejes del gráfico.
            n_period_return (int): Periodo en el que se excede la probabilidad de excedencia.
        """
        self.key_dict = key_dict
        self.colormap_name = colormap_name
        self.formats = formats
        self.labels = labels
        self.n_period_return = n_period_return
        self.poe = poe
        self.spc_acc = spc_acc
        self.df = df
        self.values = None

    def calc_weight(self):
        """Calcula los valores ponderados a partir del dataframe."""
        z_col = self.df[self.key_dict["z"]]
        z_sum = z_col.sum()
        return tuple(
            np.dot(self.df[self.key_dict[key]], z_col) / z_sum
            for key in ["y", "x", "color"]
        )

    def calc_return_prd(self):
        """Calcula y redondea Tr al valor más cercano en la lista predefinida."""
        tr_value = 1 / (1 - (1 - self.poe) ** (1 / self.n_period_return))
        return min(RETURN_PRD_LST, key=lambda x: abs(tr_value - x))

    def process_data(self):
        """Procesa un dataframe para calcular pesos y crear gráficos."""
        tr = self.calc_return_prd()
        mag_wt, dist_wt, eps_wt = self.calc_weight()
        self.values = {
            "spc_acc": self.spc_acc,
            "tr": tr,
            "mag_wt": mag_wt,
            "dist_wt": dist_wt,
            "eps_wt": eps_wt,
        }

    def create_description(self, spc_acc, tr, mag_wt, dist_wt, eps_wt):
        """Crea el texto para la leyenda del gráfico."""
        return f"""
{str(spc_acc).replace('.', SEP_DECIMAL)}
Tr = {str(tr).replace('.', SEP_DECIMAL)} años
M = {str(f"{mag_wt:.2f}").replace('.', SEP_DECIMAL)}
R = {str(f"{dist_wt:.1f}").replace('.', SEP_DECIMAL)} km
ε = {str(f"{eps_wt:.2f}").replace('.', SEP_DECIMAL)}
    """

    def generate_3d_chart(
        self,
        name,
        description,
        figsize=(15, 15),
        box_position={"x": 0.75, "y": 0.65},
        box_size={"width": 0.7, "height": 0.3},
        **kwargs,
    ):
        """Genera y guarda un gráfico 3D a partir del dataframe."""
        # Crear la instancia del gráfico 3D
        chart = BarChart3D(self.df, self.key_dict, figsize=figsize, **kwargs)

        # Crear y guardar el gráfico
        chart.create_plot(colormap_name=self.colormap_name, **self.labels)
        chart.add_textbox(
            text=description.strip(), position=box_position, box_size=box_size
        )
        chart.save_plot(filename=name, formats=self.formats)

        # Dar formato a los 'png'
        if "png" in self.formats:
            crop_image(f"{name}.png")
