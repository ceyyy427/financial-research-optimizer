"""Flatten JSON records without losing the raw source reference."""


def flatten_record(record, prefix=""):
    output = {}
    for key, value in (record or {}).items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            output.update(flatten_record(value, name))
        else:
            output[name] = value
    return output


def json_to_rows(payload, record_path=None):
    value = payload
    for part in (record_path or []):
        value = value[part]
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        raise ValueError("JSON record path must resolve to an object or list")
    return [flatten_record(item) if isinstance(item, dict) else {"value": item} for item in value]
