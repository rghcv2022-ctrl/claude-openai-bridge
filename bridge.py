def resolve_upstream_model(requested_model, default_model, model_aliases):
    if requested_model:
        return model_aliases.get(requested_model, requested_model)
    return default_model
