# +++++++++++ DJANGO +++++++++++
import os
import sys

# === STEP 1: ADD YOUR PROJECT PATH ===
# Replace with YOUR actual project path
path = '/home/mehruemm99/django_portfolio'
if path not in sys.path:
    sys.path.insert(0, path)

# === STEP 2: SET DJANGO SETTINGS MODULE ===
# Replace 'django_portfolio' with YOUR project name
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_portfolio.settings'

# === STEP 3: ACTIVATE VIRTUAL ENVIRONMENT ===
virtualenv_path = '/home/mehruemm99/.virtualenvs/django3'
activate_this = os.path.join(virtualenv_path, 'bin', 'activate_this.py')

# Check if activate_this.py exists
if os.path.exists(activate_this):
    with open(activate_this) as f:
        exec(f.read(), {'__file__': activate_this})
else:
    # Alternative method if activate_this.py doesn't exist
    activate_this = os.path.join(virtualenv_path, 'bin', 'activate')
    exec(open(activate_this).read(), dict(__file__=activate_this))

# === STEP 4: INITIALIZE DJANGO ===
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()