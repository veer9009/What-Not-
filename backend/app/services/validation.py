def revalidate_patch(model_type, data):
    """Preserve omitted fields and validate raw values before serialization."""
    if isinstance(data, model_type):
        data = {key: getattr(data, key) for key in data.model_fields_set}
    return model_type.model_validate(data)
