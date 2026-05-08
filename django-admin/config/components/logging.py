import os
from pathlib import Path

SQL_DEBUG = os.environ.get('SQL_DEBUG', 'False').lower() in (
    '1',
    'true',
    'yes',
)

if SQL_DEBUG:
    SQL_LOG_FILE = os.environ.get('SQL_LOG_FILE', '/tmp/sql_queries.log')
    sql_log_path = Path(SQL_LOG_FILE)
    log_dir = sql_log_path.parent
    can_write_sql_file = False
    if log_dir.exists() and os.access(log_dir, os.W_OK):
        file_is_writable = (
            (not sql_log_path.exists())
            or os.access(sql_log_path, os.W_OK)
        )
        if file_is_writable:
            try:
                with open(sql_log_path, 'a', encoding='utf-8'):
                    pass
                can_write_sql_file = True
            except OSError:
                can_write_sql_file = False

    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    }

    db_backend_handlers = ['console']
    if can_write_sql_file:
        handlers['sql_file'] = {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': SQL_LOG_FILE,
            'formatter': 'simple',
        }
        db_backend_handlers.append('sql_file')

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': (
                    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                ),
            },
        },
        'handlers': handlers,
        'loggers': {
            'django.db.backends': {
                'handlers': db_backend_handlers,
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }
else:
    LOGGING = {}
