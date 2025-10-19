import itertools
import reportlab.lib.pagesizes

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph

from svglib.svglib import svg2rlg
from reportlab.lib.pagesizes import landscape, portrait, A4

from libs.config.config_variables import REPORT_CONFIG_DIR

from libs.helpers.toml_helpers import load_toml


def load_svg(svg_path, scale):
    """Carga un archivo SVG y ajusta su escala.

    Args:
        svg_path (str): Ruta del archivo SVG.
        scale (float): Factor de escala.

    Returns:
        Drawing: Objeto de dibujo ajustado.
    """
    drawing = svg2rlg(svg_path)
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)
    return drawing


class ReportBuilder:
    """Construye reportes PDF personalizados con tablas y estilos configurables.

    Esta clase maneja la generación de reportes PDF basados en configuraciones TOML,
    permitiendo personalizar estilos, dimensiones y contenido de las tablas.

    Attributes:
        sample (dict): Configuración cargada del archivo TOML.
        theme_color: Color principal del tema del reporte.
        theme_color_font: Color de fuente del tema.
        width_font_scale (float): Factor de escala para el ancho de la fuente.
        rows (int): Número de filas en la tabla.
        cols (int): Número de columnas en la tabla.
    """

    def __init__(self, sample, theme_color, theme_color_font, **kwargs):
        """Inicializa el constructor de reportes.

        Args:
            sample (str): Nombre del archivo de configuración TOML.
            theme_color: Color principal del tema.
            theme_color_font: Color de fuente del tema.
            **kwargs: Atributos adicionales para el reporte.
        """

        self.sample = load_toml(sample, REPORT_CONFIG_DIR)
        self.theme_color = theme_color
        self.theme_color_font = theme_color_font
        self.width_font_scale = self.sample["settings"]["width_font_scale"]
        self.rows = len(self.sample["table"]["color"])
        self.cols = len(self.sample["table"]["color"][0])
        self.update_theme_colors(
            ["color", "font_color"], ["theme_color", "theme_color_font"]
        )
        self.set_attributes(kwargs)
        self.adjust_font_size(["project_code", "project_name", "num_item"])
        self.wrap_text_attributes(["project_name", "chart_title"])

    def update_theme_colors(self, attributes, values):
        """Actualiza los colores del tema en la configuración de la tabla.

        Args:
            attributes (list): Lista de atributos a actualizar.
            values (list): Lista de valores correspondientes.
        """

        def update_theme_color(attribute, value):
            attribute_value = getattr(self, value)
            if self.sample["table"][attribute][row][col] == value:
                self.sample["table"][attribute][row][col] = attribute_value

        for row in range(self.rows):
            for col in range(self.cols):
                for attribute, value in zip(attributes, values):
                    update_theme_color(attribute, value)

    def set_attributes(self, attributes):
        """Establece atributos adicionales para el reporte.

        Args:
            attributes (dict): Diccionario de atributos y valores.
        """
        for key, value in attributes.items():
            setattr(self, key, value)

    def create_paragraph(self, text, row, col):
        """Crea un párrafo con estilo personalizado.

        Args:
            text (str): Texto del párrafo.
            row (int): Índice de la fila.
            col (int): Índice de la columna.

        Returns:
            Paragraph: Párrafo con estilo aplicado.
        """
        style = ParagraphStyle(
            name="Normal",
            alignment=self.get_alignment(row, col),
            textColor=self.sample["table"]["font_color"][row][col],
            fontSize=self.sample["table"]["font_size"][row][col],
            fontName=self.sample["table"]["font_name"][row][col],
            leading=self.sample["table"]["font_size"][row][col],
            leftPadding=self.sample["table"]["padding_left"][row][col],
            rightPadding=self.sample["table"]["padding_right"][row][col],
            topPadding=self.sample["table"]["padding_top"][row][col],
            bottomPadding=self.sample["table"]["padding_bottom"][row][col],
        )
        return Paragraph(text, style)

    def wrap_text(self, text, row, col):
        """Envuelve el texto en un párrafo si es una cadena.

        Args:
            text (str): Texto a envolver.
            row (int): Índice de la fila.
            col (int): Índice de la columna.

        Returns:
            Paragraph or str: Párrafo envuelto o texto original.
        """
        if isinstance(text, str):
            return self.create_paragraph(text, row, col)
        return text

    def get_alignment(self, row, col):
        """Obtiene la alineación de texto para una celda.

        Args:
            row (int): Índice de la fila.
            col (int): Índice de la columna.

        Returns:
            int: Código de alineación.
        """
        align_map = {"LEFT": 0, "CENTER": 1, "RIGHT": 2, "JUSTIFY": 4}
        return align_map.get(self.sample["table"]["align"][row][col], 0)

    def create_cell_styles(self):
        """Crea estilos para las celdas de la tabla.

        Returns:
            list: Lista de estilos de celdas.
        """
        table_styles = self.sample["table"]
        styles = []

        def create_cell_style(style, style_name, attributes, row, col):
            style_attributes = tuple(
                table_styles[attribute][row][col] for attribute in attributes
            )
            style.append((style_name, (col, row), (col, row), *style_attributes))

        for row, col in itertools.product(range(self.rows), range(self.cols)):
            styles_mapping = {
                "GRID": ["size_border", "color_border"],
                "ALIGN": ["align"],
                "VALIGN": ["valign"],
                "BACKGROUND": ["color"],
                "FONTSIZE": ["font_size"],
                "TEXTCOLOR": ["font_color"],
                "FONTNAME": ["font_name"],
                "LEFTPADDING": ["padding_left"],
                "RIGHTPADDING": ["padding_right"],
                "TOPPADDING": ["padding_top"],
                "BOTTOMPADDING": ["padding_bottom"],
            }

            for style, attributes in styles_mapping.items():
                create_cell_style(styles, style, attributes, row, col)

        return styles

    def apply_cell_styles(self, table):
        """Aplica estilos a las celdas de la tabla.

        Args:
            table (Table): Tabla a la que se aplicarán los estilos.
        """
        styles = self.create_cell_styles()
        table.setStyle(TableStyle(styles))

    def create_table_style(self, outer_border_style, outer_border_size):
        """Crea estilos para la tabla principal.

        Args:
            outer_border_style: Estilo del borde exterior.
            outer_border_size (float): Grosor del borde exterior.

        Returns:
            TableStyle: Estilos de la tabla.
        """
        spans = self.sample["spans"]["values"]
        styles = [
            (
                "SPAN",
                (span["start"][1], span["start"][0]),
                (span["end"][1], span["end"][0]),
            )
            for span in spans
        ]
        styles.append(
            ("OUTLINE", (0, 0), (-1, -1), outer_border_size, outer_border_style)
        )
        return TableStyle(styles)

    def create_table_data(self):
        """Crea los datos para la tabla.

        Returns:
            list: Datos de la tabla.
        """
        data = [["***" for _ in range(self.cols)] for _ in range(self.rows)]
        self.populate_cell_positions(data)
        self.populate_texts_positions(data)
        return data

    def populate_cell_positions(self, data):
        """Llena las posiciones de las celdas con datos.

        Args:
            data (list): Datos de la tabla.
        """
        cell_positions = self.sample["cell_positions"]
        for key, value in cell_positions.items():
            data[value[0]][value[1]] = getattr(self, key)

    def populate_texts_positions(self, data):
        """Llena las posiciones de texto en la tabla.

        Args:
            data (list): Datos de la tabla.
        """
        texts_positions = self.sample["texts_positions"]
        for key, value in texts_positions.items():
            data[value[0]][value[1]] = self.sample["texts"][key]

    def create_table(self, margins, outer_border_style, outer_border_size):
        """Crea la tabla principal del reporte con los estilos y dimensiones especificados.

        Args:
            margins (float): Márgenes de la página en puntos.
            outer_border_style: Estilo del borde exterior.
            outer_border_size (float): Grosor del borde exterior.

        Returns:
            tuple: (Table, float, list) Tabla generada, altura del contenido y alturas de filas.
        """
        page_width, page_height = self.get_page_dimensions()
        content_width, content_height = self.get_content_dimensions(
            page_width, page_height, margins
        )
        adjusted_column_widths, adjusted_row_heights = self.get_adjusted_dimensions(
            content_width, content_height
        )

        data = self.create_table_data()
        table = Table(
            data, colWidths=adjusted_column_widths, rowHeights=adjusted_row_heights
        )
        self.apply_cell_styles(table)
        table.setStyle(self.create_table_style(outer_border_style, outer_border_size))

        return table, content_height, adjusted_row_heights

    def get_page_dimensions(self):
        """Obtiene las dimensiones de la página según la orientación y tamaño.

        Returns:
            tuple: Ancho y alto de la página en puntos.
        """
        page_orientation = self.sample["page"]["orientation"]
        paper_size = getattr(
            reportlab.lib.pagesizes, self.sample["page"]["size"].upper(), A4
        )

        if page_orientation == "landscape":
            return landscape(paper_size)
        else:
            return portrait(paper_size)

    def get_content_dimensions(self, page_width, page_height, margins):
        """Calcula las dimensiones del contenido dentro de los márgenes.

        Args:
            page_width (float): Ancho de la página.
            page_height (float): Alto de la página.
            margins (float): Márgenes de la página.

        Returns:
            tuple: Ancho y alto del contenido en puntos.
        """
        content_width = page_width - 2 * margins
        content_height = page_height - 2 * margins
        return content_width, content_height

    def get_adjusted_dimensions(self, content_width, content_height):
        """Ajusta las dimensiones de columnas y filas según el contenido disponible.

        Args:
            content_width (float): Ancho del contenido.
            content_height (float): Alto del contenido.

        Returns:
            tuple: Listas de anchos de columnas y alturas de filas ajustadas.
        """
        column_widths = self.sample["column_widths"]["values"]
        row_heights = self.sample["row_heights"]["values"]

        total_width = sum(column_widths)
        scale_factor_width = content_width / total_width
        adjusted_column_widths = [w * scale_factor_width * 0.9 for w in column_widths]

        total_height = sum(row_heights)
        scale_factor_height = content_height / total_height
        adjusted_row_heights = [h * scale_factor_height * 0.9 for h in row_heights]

        return adjusted_column_widths, adjusted_row_heights

    def generate_pdf(self, pdf_path="output.pdf"):
        """Genera el archivo PDF final con el reporte.

        Args:
            pdf_path (str): Ruta donde se guardará el PDF. Por defecto 'output.pdf'.
        """
        margins = self.sample["page"]["margins"]
        outer_border_style = colors.black
        outer_border_size = self.sample["border"]["size"]

        table, content_height, adjusted_row_heights = self.create_table(
            margins, outer_border_style, outer_border_size
        )

        vertical_padding = self.calculate_vertical_padding(
            content_height, adjusted_row_heights
        )
        doc = self.create_report(pdf_path, margins)
        elements = [Spacer(1, vertical_padding), table]
        doc.build(elements)

    def calculate_vertical_padding(self, content_height, adjusted_row_heights):
        """Calcula el espacio vertical disponible para el contenido.

        Args:
            content_height (float): Altura del contenido.
            adjusted_row_heights (list): Alturas ajustadas de las filas.

        Returns:
            float: Espacio vertical disponible en puntos.
        """
        available_space = content_height - sum(adjusted_row_heights)
        return available_space / 2

    def create_report(self, pdf_path, margins):
        """Crea el documento PDF con los márgenes especificados.

        Args:
            pdf_path (str): Ruta del archivo PDF.
            margins (float): Márgenes de la página.

        Returns:
            SimpleDocTemplate: Documento PDF configurado.
        """
        page_orientation = self.sample["page"]["orientation"]
        paper_size = getattr(
            reportlab.lib.pagesizes, self.sample["page"]["size"].upper(), A4
        )

        return SimpleDocTemplate(
            pdf_path,
            pagesize=(
                landscape(paper_size)
                if page_orientation == "landscape"
                else portrait(paper_size)
            ),
            leftMargin=margins,
            rightMargin=margins,
            topMargin=margins,
            bottomMargin=margins,
        )

    def wrap_text_attributes(self, attributes):
        """Envuelve los atributos de texto en párrafos.

        Args:
            attributes (list): Lista de atributos a envolver.
        """
        for attribute in attributes:
            row, col = self.sample["cell_positions"][attribute]
            setattr(self, attribute, self.wrap_text(getattr(self, attribute), row, col))

    def adjust_font_size(self, attributes):
        """Ajusta el tamaño de la fuente para que el texto quepa en la celda.

        Reduce iterativamente el tamaño de la fuente hasta que el texto quepa
        en el ancho máximo disponible de la celda.

        Args:
            attributes (list): Lista de atributos cuyos tamaños de fuente se ajustarán.
        """
        for attribute in attributes:
            row, col = self.sample["cell_positions"][attribute]
            text = getattr(self, attribute)
            font_size = self.sample["table"]["font_size"][row][col]

            max_width = self.get_max_width(row, col)

            while self.get_text_width(text, font_size) >= max_width and font_size > 1:
                font_size -= 0.5
            self.sample["table"]["font_size"][row][col] = font_size

    def get_max_width(self, row, col):
        """Calcula el ancho máximo disponible para una celda.

        Args:
            row (int): Índice de la fila.
            col (int): Índice de la columna.

        Returns:
            float: Ancho máximo disponible en puntos.
        """
        max_width = self.sample["column_widths"]["values"][col]
        for span in self.sample["spans"]["values"]:
            if span["start"] == [row, col] and span["start"][0] == span["end"][0]:
                for c in range(span["start"][1], span["end"][1] + 1):
                    max_width += self.sample["column_widths"]["values"][c]
        padding_left = self.sample["table"]["padding_left"][row][col]
        padding_right = self.sample["table"]["padding_right"][row][col]
        max_width -= padding_left + padding_right
        return max_width

    def get_text_width(self, text, font_size):
        """Estima el ancho de un texto con un tamaño de fuente específico.

        Args:
            text (str): Texto a medir.
            font_size (float): Tamaño de la fuente.

        Returns:
            float: Ancho estimado del texto.
        """
        # This is a simplified estimation of text width.
        # For more accurate results, use a library like PIL.
        return len(text) * font_size * self.width_font_scale
