import os


# Default Kafka configuration, resolved from environment variables.
# Override any value by passing kwargs to get_kafka_config().

_DEFAULTS = {
    "bootstrap_servers": "localhost:29092",
    "consumer_group_id": "default-group",
    "batch_size": 10,
    "batch_timeout_s": 20,
}

_ENV_MAP = {
    "bootstrap_servers": "KAFKA_BOOTSTRAP_SERVERS",
    "consumer_group_id": "KAFKA_CONSUMER_GROUP_ID",
    "batch_size": "KAFKA_BATCH_SIZE",
    "batch_timeout_s": "KAFKA_BATCH_TIMEOUT_S",
}


def get_kafka_config(**overrides) -> dict:
    """
    Build a Kafka config dict.

    Resolution order (highest priority first):
        1. Explicit kwargs passed to this function
        2. Environment variables (KAFKA_BOOTSTRAP_SERVERS, etc.)
        3. Hard-coded defaults above

    Returns:
        dict with keys: bootstrap_servers, consumer_group_id,
        batch_size (int), batch_timeout_s (int).
    """
    config = {}
    for key, default in _DEFAULTS.items():
        env_val = os.environ.get(_ENV_MAP[key])

        if key in overrides and overrides[key] is not None:
            config[key] = overrides[key]
        elif env_val is not None:
            config[key] = type(default)(env_val)
        else:
            config[key] = default

    return config
