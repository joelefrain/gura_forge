import pandas as pd

from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

from libs.config.config_variables import TABLE_CONFIG_DIR

from libs.helpers.toml_helpers import load_toml

MIN_FONT_SIZE = 2
MIN_LEADING_FACTOR = 1.0
MAX_ITERATIONS = 200
STEP_REDUCTION = 0.95
LEADING_ESTIMATION_FACTOR = 0.85


class TableHandler:
    def __init__(self, style_name="default"):
        """
        Inicializa el manejador de tablas con un estilo específico
        :param style_name: Nombre del archivo de estilo (sin extensión .toml)
        """
        self.style_name = style_name
        self.style_config = load_toml(style_name, TABLE_CONFIG_DIR)

    def create_table(self, df: pd.DataFrame, width=None, height=None):
        """
        Crea una tabla estilizada a partir de un DataFrame y la configuración de estilo
        :param df: DataFrame de pandas
        :param width: Ancho opcional de la tabla
        :param height: Alto opcional de la tabla
        :return: Objeto Table de reportlab
        """
        # Obtener configuración de estilo
        table_cfg = self.style_config.get("table", {})
        head_cfg = self.style_config.get("header", {})
        body_cfg = self.style_config.get("body", {})

        # Determinar dimensiones finales
        final_width = width if width is not None else table_cfg.get("width")
        final_height = height if height is not None else table_cfg.get("height")

        ncols = len(df.columns)
        nrows = len(df) + 1

        # Preparar datos con ajustes de texto si es necesario
        data = self._prepare_table_data(df, final_width, head_cfg, body_cfg)

        # No usar rowHeights fijos cuando height es límite máximo
        # Solo usar colWidths para width
        colWidths = None
        rowHeights = None

        if final_width:
            colWidths = [float(final_width) / ncols] * ncols

        # Para height, no forzar altura fija de filas, solo ajustar fuente si es necesario
        table = Table(data, colWidths=colWidths, rowHeights=rowHeights)

        # Aplicar estilo con ajustes de fuente si es necesario
        style = self._build_table_style(final_height, nrows, final_width, ncols, data)
        table.setStyle(style)
        return table

    def _prepare_table_data(self, df, width, head_cfg, body_cfg):
        """
        Prepara los datos de la tabla, aplicando saltos de línea si se especifica ancho
        """
        data = []
        ncols = len(df.columns)

        # Obtener tamaños de fuente para cálculos de wrapping
        head_font_size = head_cfg.get("fontSize", 12)
        body_font_size = body_cfg.get("fontSize", 10)

        # Preparar encabezados
        headers = list(df.columns)
        if width:
            col_width = width / ncols
            # Aplicar saltos de línea a los encabezados si es necesario
            headers = [
                self._wrap_text(str(header), col_width, head_font_size)
                for header in headers
            ]
        data.append(headers)

        # Preparar datos del cuerpo
        for _, row in df.iterrows():
            row_data = []
            for value in row:
                if width:
                    col_width = width / ncols
                    # Aplicar saltos de línea al contenido si es necesario
                    wrapped_value = self._wrap_text(
                        str(value), col_width, body_font_size
                    )
                    row_data.append(wrapped_value)
                else:
                    row_data.append(str(value))
            data.append(row_data)

        return data

    def _build_table_style(
        self, height=None, nrows=None, width=None, ncols=None, data=None
    ):
        """
        Construye el TableStyle de reportlab a partir de la configuración
        """
        cfg = self.style_config
        ts = []

        # Obtener configuraciones
        head_cfg = cfg.get("header", {})
        body_cfg = cfg.get("body", {})

        # Calcular tamaños de fuente ajustados
        head_font_size = head_cfg.get("fontSize", 12)
        body_font_size = body_cfg.get("fontSize", 10)

        # Obtener valores de leading originales
        head_leading = head_cfg.get("LEADING", head_font_size * 1.2)
        body_leading = body_cfg.get("LEADING", body_font_size * 1.2)

        # Ajustar tamaños de fuente y leading basado en dimensiones disponibles
        if height and nrows:
            head_font_size, body_font_size, head_leading, body_leading = (
                self._calculate_font_and_leading_for_height(
                    height,
                    nrows,
                    head_font_size,
                    body_font_size,
                    head_leading,
                    body_leading,
                    data,
                )
            )

        if width and ncols and data:
            head_font_size, body_font_size = self._calculate_font_sizes_for_width(
                width, ncols, data, head_font_size, body_font_size
            )

        # Aplicar estilos de encabezado
        if head_cfg:
            ts.append(
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    self._parse_color(head_cfg.get("background", "#CCCCCC")),
                )
            )
            ts.append(
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    self._parse_color(head_cfg.get("textColor", "#000000")),
                )
            )
            if "fontName" in head_cfg:
                ts.append(("FONTNAME", (0, 0), (-1, 0), head_cfg["fontName"]))

            ts.append(("FONTSIZE", (0, 0), (-1, 0), head_font_size))
            ts.append(("LEADING", (0, 0), (-1, 0), head_leading))

            # Otros estilos específicos del header
            for key, value in head_cfg.items():
                if key.upper() not in [
                    "BACKGROUND",
                    "TEXTCOLOR",
                    "FONTNAME",
                    "FONTSIZE",
                    "LEADING",
                ]:
                    ts.append((key.upper(), (0, 0), (-1, 0), value))

            # Alineación vertical para encabezados
            ts.append(("VALIGN", (0, 0), (-1, 0), "MIDDLE"))

        # Aplicar estilos del cuerpo
        if body_cfg:
            ts.append(
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    self._parse_color(body_cfg.get("background", "#FFFFFF")),
                )
            )
            ts.append(
                (
                    "TEXTCOLOR",
                    (0, 1),
                    (-1, -1),
                    self._parse_color(body_cfg.get("textColor", "#000000")),
                )
            )
            if "fontName" in body_cfg:
                ts.append(("FONTNAME", (0, 1), (-1, -1), body_cfg["fontName"]))

            ts.append(("FONTSIZE", (0, 1), (-1, -1), body_font_size))
            ts.append(("LEADING", (0, 1), (-1, -1), body_leading))

            # Otros estilos específicos del body
            for key, value in body_cfg.items():
                if key.upper() not in [
                    "BACKGROUND",
                    "TEXTCOLOR",
                    "FONTNAME",
                    "FONTSIZE",
                    "LEADING",
                ]:
                    ts.append((key.upper(), (0, 1), (-1, -1), value))

            # Alineación vertical para el cuerpo
            ts.append(("VALIGN", (0, 1), (-1, -1), "TOP"))

        # Aplicar bordes
        border_cfg = cfg.get("borders", {})
        if border_cfg:
            color = self._parse_color(border_cfg.get("color", "#000000"))
            width = border_cfg.get("width", 1)
            ts.append(("GRID", (0, 0), (-1, -1), width, color))

        # Aplicar otros estilos generales de tabla
        table_styles = cfg.get("table", {})
        for key, value in table_styles.items():
            if key.upper() not in [
                "WIDTH",
                "HEIGHT",
            ]:  # Excluir dimensiones ya manejadas
                ts.append((key.upper(), (0, 0), (-1, -1), value))

        return TableStyle(ts)

    def _calculate_font_and_leading_for_height(
        self,
        height,
        nrows,
        head_font_size,
        body_font_size,
        head_leading,
        body_leading,
        data=None,
    ):
        """
        Calcula los tamaños de fuente y leading apropiados para no exceder la altura máxima
        Usa reducción iterativa agresiva hasta que la tabla quepa perfectamente
        """

        # Mantener proporciones originales
        head_body_ratio = head_font_size / body_font_size if body_font_size > 0 else 1.2
        head_leading_ratio = (
            head_leading / head_font_size if head_font_size > 0 else 1.2
        )
        body_leading_ratio = (
            body_leading / body_font_size if body_font_size > 0 else 1.2
        )

        # Asegurar ratios mínimos para legibilidad
        head_leading_ratio = max(MIN_LEADING_FACTOR, head_leading_ratio)
        body_leading_ratio = max(MIN_LEADING_FACTOR, body_leading_ratio)

        # Comenzar con los valores originales
        current_body_size = body_font_size
        current_head_size = head_font_size
        current_body_leading = body_leading
        current_head_leading = head_leading

        # Calcular altura inicial
        estimated_height = self._estimate_table_height_with_leading(
            nrows,
            current_head_size,
            current_body_size,
            current_head_leading,
            current_body_leading,
            data,
        )

        # Si ya cabe, retornar valores originales
        if estimated_height <= height:
            return (
                current_head_size,
                current_body_size,
                current_head_leading,
                current_body_leading,
            )

        # Método 1: Reducción proporcional
        # Calcular factor de reducción necesario
        reduction_factor = height / estimated_height
        safety_margin = 0.95  # 5% de margen de seguridad
        reduction_factor *= safety_margin

        # Aplicar reducción inicial
        current_body_size = max(MIN_FONT_SIZE, current_body_size * reduction_factor)
        current_head_size = max(MIN_FONT_SIZE, current_body_size * head_body_ratio)
        current_body_leading = max(
            current_body_size * MIN_LEADING_FACTOR,
            current_body_size * body_leading_ratio,
        )
        current_head_leading = max(
            current_head_size * MIN_LEADING_FACTOR,
            current_head_size * head_leading_ratio,
        )

        # Método 2: Refinamiento iterativo
        iteration = 0
        max_iterations = MAX_ITERATIONS
        step_reduction = STEP_REDUCTION

        while iteration < max_iterations:
            estimated_height = self._estimate_table_height_with_leading(
                nrows,
                current_head_size,
                current_body_size,
                current_head_leading,
                current_body_leading,
                data,
            )

            # Si la altura está dentro del límite (con pequeño margen), terminar
            if estimated_height <= height * 1.02:  # 2% de tolerancia
                break

            # Si aún no cabe, reducir más
            if estimated_height > height:
                # Calcular nueva reducción basada en el exceso actual
                excess_factor = estimated_height / height
                aggressive_reduction = min(step_reduction, 0.95 / excess_factor)

                current_body_size = max(
                    MIN_FONT_SIZE, current_body_size * aggressive_reduction
                )
                current_head_size = max(
                    MIN_FONT_SIZE, current_body_size * head_body_ratio
                )
                current_body_leading = max(
                    current_body_size * MIN_LEADING_FACTOR,
                    current_body_size * body_leading_ratio,
                )
                current_head_leading = max(
                    current_head_size * MIN_LEADING_FACTOR,
                    current_head_size * head_leading_ratio,
                )

                # Si llegamos al mínimo absoluto, reducir también el leading
                if current_body_size <= MIN_FONT_SIZE:
                    current_body_leading = max(
                        MIN_FONT_SIZE, current_body_leading * step_reduction
                    )
                    current_head_leading = max(
                        MIN_FONT_SIZE, current_head_leading * step_reduction
                    )

            iteration += 1

        # Método 3: Última verificación con leading mínimo si es necesario
        final_height = self._estimate_table_height_with_leading(
            nrows,
            current_head_size,
            current_body_size,
            current_head_leading,
            current_body_leading,
            data,
        )

        if final_height > height:
            # Reducir leading al mínimo absoluto
            current_body_leading = current_body_size
            current_head_leading = current_head_size

            # Verificar si aún necesitamos reducir más
            final_height = self._estimate_table_height_with_leading(
                nrows,
                current_head_size,
                current_body_size,
                current_head_leading,
                current_body_leading,
                data,
            )

            if final_height > height:
                # Última reducción del font size
                final_reduction = height / final_height * 0.9
                current_body_size = max(
                    MIN_FONT_SIZE, current_body_size * final_reduction
                )
                current_head_size = max(
                    MIN_FONT_SIZE, current_body_size * head_body_ratio
                )
                current_body_leading = current_body_size
                current_head_leading = current_head_size

        return (
            current_head_size,
            current_body_size,
            current_head_leading,
            current_body_leading,
        )

    def _calculate_text_height(self, text, font_size, leading):
        """
        Calcula la altura real que ocupará un texto dado el font size y leading
        Considera cómo ReportLab maneja realmente el espaciado de texto
        """
        if not text:
            return leading

        lines = str(text).count("\n") + 1

        if lines == 1:
            # Para una sola línea, la altura efectiva es el leading
            # pero nunca menor que el font_size
            return max(font_size, leading)
        else:
            # Para múltiples líneas:
            # - La primera línea ocupa el font_size como altura base
            # - Las líneas adicionales usan el leading como espaciado
            # - Pero el leading nunca debe ser menor que el font_size
            effective_leading = max(font_size, leading)
            return font_size + (effective_leading * (lines - 1))

    def _estimate_table_height_with_leading(
        self,
        nrows,
        head_font_size,
        body_font_size,
        head_leading,
        body_leading,
        data=None,
    ):
        """
        Estima la altura total de la tabla considerando font size y leading específicos
        Usa cálculo preciso de altura de texto que considera el tamaño real de la letra
        """
        total_height = 0

        # Padding adicional por celda (margen interno típico de reportlab)
        cell_padding_vertical = 4  # Reducido de 6 para ser más conservador
        border_width = 1  # Ancho típico de bordes

        # Altura del header
        if data and len(data) > 0:
            # Encontrar la celda con más líneas en el header
            max_header_height = 0
            for cell in data[0]:
                cell_height = self._calculate_text_height(
                    cell, head_font_size, head_leading
                )
                max_header_height = max(max_header_height, cell_height)

            header_height = (
                max_header_height + (cell_padding_vertical * 2) + border_width
            )
        else:
            # Header por defecto
            header_height = (
                max(head_font_size, head_leading)
                + (cell_padding_vertical * 2)
                + border_width
            )

        total_height += header_height

        # Altura del cuerpo
        body_rows = nrows - 1
        if body_rows > 0 and data and len(data) > 1:
            # Calcular altura para cada fila del cuerpo
            for row_idx in range(1, len(data)):  # Empezar desde 1 para excluir header
                if row_idx < len(data):
                    max_row_height = 0
                    for cell in data[row_idx]:
                        cell_height = self._calculate_text_height(
                            cell, body_font_size, body_leading
                        )
                        max_row_height = max(max_row_height, cell_height)

                    # Altura total de esta fila
                    row_height = (
                        max_row_height + (cell_padding_vertical * 2) + border_width
                    )
                    total_height += row_height
        else:
            # Si no hay datos específicos, usar estimación promedio
            if body_rows > 0:
                avg_body_content_height = max(body_font_size, body_leading)
                avg_body_height = (
                    avg_body_content_height + (cell_padding_vertical * 2) + border_width
                )
                total_height += avg_body_height * body_rows

        return total_height

    def _calculate_font_sizes_for_height(
        self, height, nrows, head_font_size, body_font_size, data=None
    ):
        """
        Método legacy mantenido para compatibilidad
        Usa el nuevo método que incluye leading
        """
        head_leading = head_font_size * 1.2
        body_leading = body_font_size * 1.2

        new_head_font_size, new_body_font_size, _, _ = (
            self._calculate_font_and_leading_for_height(
                height,
                nrows,
                head_font_size,
                body_font_size,
                head_leading,
                body_leading,
                data,
            )
        )

        return new_head_font_size, new_body_font_size

    def _estimate_table_height(self, nrows, head_font_size, body_font_size, data=None):
        """
        Método legacy mantenido para compatibilidad
        Usa el nuevo método que incluye leading
        """
        head_leading = head_font_size * LEADING_ESTIMATION_FACTOR
        body_leading = body_font_size * LEADING_ESTIMATION_FACTOR

        return self._estimate_table_height_with_leading(
            nrows, head_font_size, body_font_size, head_leading, body_leading, data
        )

    def _calculate_font_sizes_for_width(
        self, width, ncols, data, head_font_size, body_font_size
    ):
        """
        Calcula los tamaños de fuente apropiados basándose en el ancho disponible
        para evitar que las palabras se corten
        """
        col_width = width / ncols

        # Encontrar la palabra más larga en cada columna
        max_word_lengths = []

        for col_idx in range(ncols):
            max_word_length = 0

            # Revisar todas las filas para esta columna
            for row_data in data:
                if col_idx < len(row_data):
                    cell_text = str(row_data[col_idx])
                    words = cell_text.split()
                    for word in words:
                        max_word_length = max(max_word_length, len(word))

            max_word_lengths.append(max_word_length)

        # Calcular el tamaño de fuente necesario para la palabra más larga
        # Aproximación: cada carácter ocupa aproximadamente 0.6 veces el tamaño de fuente en ancho
        char_width_factor = 0.6

        # Encontrar el tamaño de fuente que permita que la palabra más larga quepa
        max_word_length_overall = max(max_word_lengths) if max_word_lengths else 1

        # Calcular tamaño de fuente máximo para que la palabra más larga quepa
        max_font_size_for_width = (col_width * 0.9) / (
            max_word_length_overall * char_width_factor
        )

        # Ajustar los tamaños de fuente
        new_body_size = min(body_font_size, max_font_size_for_width)
        new_body_size = max(3, new_body_size)  # Mínimo legible

        new_head_size = min(head_font_size, max_font_size_for_width)
        new_head_size = max(
            new_body_size, new_head_size
        )  # Header nunca más pequeño que body

        return new_head_size, new_body_size

    def _wrap_text(self, text, max_width_per_col, font_size=10):
        """
        Aplica saltos de línea al texto basado en el ancho disponible y tamaño de fuente
        Asegura que las palabras no se corten
        """
        # Factor de caracteres por unidad de ancho basado en el tamaño de fuente
        char_width_factor = 0.6
        max_chars = max(5, int(max_width_per_col / (font_size * char_width_factor)))

        words = text.split()
        if not words:
            return text

        lines = []
        current_line = ""

        for word in words:
            # Si la palabra sola es más larga que el ancho máximo, la ponemos en su propia línea
            if len(word) > max_chars:
                if current_line:
                    lines.append(current_line.strip())
                    current_line = ""
                lines.append(word)
            else:
                # Verificar si agregar esta palabra excede el límite
                test_line = current_line + " " + word if current_line else word
                if len(test_line) <= max_chars:
                    current_line = test_line
                else:
                    # La línea actual está completa, comenzar una nueva
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word

        # Agregar la última línea si existe
        if current_line:
            lines.append(current_line.strip())

        return "\n".join(lines)

    def _parse_color(self, color_str):
        """
        Convierte un string de color hexadecimal a un objeto de color de reportlab
        """
        if isinstance(color_str, tuple):
            return color_str
        if color_str.startswith("#"):
            color_str = color_str.lstrip("#")
            return colors.HexColor("#" + color_str)
        return getattr(colors, color_str, colors.black)
