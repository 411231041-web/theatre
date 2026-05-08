import os

# Security / environment-driven settings
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'project_name')
PROJECT_DESCRIPTION = os.environ.get(
    'PROJECT_DESCRIPTION',
    'project_description',
)
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False').lower() in (
    '1',
    'true',
    'yes',
)
ALLOWED_HOSTS = [
    host
    for host in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if host
]
INTERNAL_IPS = [
    ip
    for ip in os.environ.get('INTERNAL_IPS', '127.0.0.1').split(',')
    if ip
]
