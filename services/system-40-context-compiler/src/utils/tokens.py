"""Token counting utilities using tiktoken."""
import tiktoken
import structlog

logger = structlog.get_logger()

_ENCODING: tiktoken.Encoding | None = None


def get_encoding() -> tiktoken.Encoding:
    """Get or create the cl100k_base encoding (lazy singleton)."""
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    """Count tokens in a text string."""
    return len(get_encoding().encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget."""
    enc = get_encoding()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])
