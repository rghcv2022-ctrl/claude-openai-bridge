import fnmatch


def resolve_upstream_model(requested_model, default_model, model_aliases):
    if requested_model:
        exact = model_aliases.get(requested_model)
        if exact:
            return exact
        for pattern, mapped in model_aliases.items():
            if "*" in pattern and fnmatch.fnmatch(requested_model, pattern):
                return mapped
        return requested_model
    return default_model
