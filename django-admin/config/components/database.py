import os

DATABASES: dict[str, dict[str, object]] = {
    "default": {
        "ENGINE": os.getenv("SQL_ENGINE"),
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("SQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("SQL_PORT", 5432),
        "OPTIONS": {
            "options": os.getenv("SQL_OPTIONS"),
        },
    }
}
