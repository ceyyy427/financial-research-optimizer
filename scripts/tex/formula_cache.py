"""Content-addressed formula cache helpers."""
import hashlib


def formula_hash(tex_source):
    return hashlib.sha256(str(tex_source).encode("utf-8")).hexdigest()
