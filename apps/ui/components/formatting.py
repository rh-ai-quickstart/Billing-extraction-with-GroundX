from typing import Dict, Any


def format_json(json_data: Dict[str, Any], indent: int = 0) -> str:
    """Recursively format JSON data as an HTML string with color-coded syntax spans."""
    if isinstance(json_data, dict):
        formatted = "{\n"
        for i, (key, value) in enumerate(json_data.items()):
            formatted += "  " * (indent + 1) + f'<span class="json-key">"{key}"</span>: '
            if isinstance(value, (dict, list)):
                formatted += format_json(value, indent + 1)
            else:
                formatted += _format_scalar(value)
            if i < len(json_data) - 1:
                formatted += ","
            formatted += "\n"
        formatted += "  " * indent + "}"
        return formatted
    elif isinstance(json_data, list):
        formatted = "[\n"
        for i, item in enumerate(json_data):
            formatted += "  " * (indent + 1)
            if isinstance(item, (dict, list)):
                formatted += format_json(item, indent + 1)
            else:
                formatted += _format_scalar(item)
            if i < len(json_data) - 1:
                formatted += ","
            formatted += "\n"
        formatted += "  " * indent + "]"
        return formatted
    return _format_scalar(json_data)


def _format_scalar(value: Any) -> str:
    """Wrap a scalar value in a styled HTML span based on its Python type."""
    if isinstance(value, str):
        return f'<span class="json-string">"{value}"</span>'
    elif isinstance(value, (int, float)):
        return f'<span class="json-number">{value}</span>'
    elif isinstance(value, bool):
        return f'<span class="json-boolean">{str(value).lower()}</span>'
    elif value is None:
        return f'<span class="json-null">null</span>'
    return str(value)
