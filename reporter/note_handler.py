from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, ListFlowable, ListItem

from libs.config.config_variables import NOTE_CONFIG_DIR

from libs.helpers.toml_helpers import load_toml


class NotesHandler:
    def __init__(self, style_name="default"):
        """
        Inicializa el manejador de notas con un estilo específico
        :param style_name: Nombre del archivo de estilo (sin extensión .toml)
        """
        self.styles = getSampleStyleSheet()
        self.style_name = style_name
        self.style_config = load_toml(style_name, NOTE_CONFIG_DIR)

    def create_notes(self, sections, title_style=None, list_style=None):
        """Crea bloques de notas con formato configurable"""
        elements = []

        for section in sections:
            section_title_style = section.get("title_style", title_style or {})
            title_element = self._create_notes_title(
                section["title"], **section_title_style
            )
            elements.append(title_element)

            section_format = section.get("format_type", "numbered")
            section_list_style = section.get("style", list_style or {})
            format_config = self.style_config["formats"].get(section_format, {})
            content_element = self._create_notes_items(
                section["content"],
                format_type=section_format,
                format_config=format_config,
                **section_list_style,
            )
            elements.append(content_element)

        return elements

    def _create_notes_title(self, title, **kwargs):
        """Crea el elemento de título con el estilo configurado"""
        title_style = self.styles["Normal"].clone(name="NotesTitle")
        title_config = self.style_config["title"]

        for key, value in title_config.items():
            setattr(title_style, key, value)

        for key, value in kwargs.items():
            setattr(title_style, key, value)

        return Paragraph(title, title_style)

    def _create_list_items(self, notes, text_style, format_config):
        """Método base para crear elementos de lista con cualquier formato"""
        config = format_config.copy()

        # Asegurar que el tamaño de la fuente del bullet coincida
        if "bulletFontSize" not in config:
            config["bulletFontSize"] = text_style.fontSize

        # Extraer leftIndent de la configuración y eliminarlo del diccionario
        left_indent = config.pop("leftIndent", 0)

        # Crear los items de la lista
        note_items = [ListItem(Paragraph(note, text_style)) for note in notes]
        return ListFlowable(note_items, leftIndent=left_indent, **config)

    def _create_notes_items(self, notes, format_type, format_config, **kwargs):
        """Crea los elementos de contenido con el estilo configurado"""
        # Create and configure text style in one step
        text_style = self.styles["Normal"].clone(name="NoteText")

        # Apply all style configurations in a single loop
        for config_dict in [self.style_config["content"], format_config, kwargs]:
            for key, value in config_dict.items():
                setattr(text_style, key, value)

        # Convert notes to list of strings in a more concise way
        if isinstance(notes, str):
            notes_str = [notes]
        else:
            notes_str = [str(note) for note in notes]

        # Handle format types
        if format_type == "paragraph":
            return Paragraph("<br/>".join(notes_str), text_style)
        elif format_type in ["bullet", "numbered", "alphabet"]:
            return self._create_list_items(notes_str, text_style, format_config)
        else:
            raise ValueError(f"Unsupported format_type: {format_type}")
