from deep_translator import GoogleTranslator


def translate_to_hindi(text: str) -> str:
    """Translate text to Hindi using Google Translate (free)."""
    try:
        translator = GoogleTranslator(source='auto', target='hi')
        # Split long text into chunks (Google Translate has char limits)
        max_chunk = 4500
        if len(text) <= max_chunk:
            return translator.translate(text)
        
        chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
        translated_chunks = [translator.translate(chunk) for chunk in chunks]
        return " ".join(translated_chunks)
    except Exception as e:
        return f"[Translation unavailable: {str(e)}]\n\n{text}"


def translate_dict_to_hindi(data: dict) -> dict:
    """Translate string values in a dict to Hindi."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str) and value:
            result[key] = translate_to_hindi(value)
        elif isinstance(value, list):
            result[key] = [translate_to_hindi(item) if isinstance(item, str) else item for item in value]
        else:
            result[key] = value
    return result
