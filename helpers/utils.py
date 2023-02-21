def n(text: str, addition=''):
    """Если text - None, то вернуть пустую строку"""
    return "" if text is None else addition + text
