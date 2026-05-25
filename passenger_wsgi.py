# Fichier pour LWS hébergement mutualisé (Passenger/cPanel)
import sys
import os

# Chemin vers votre projet sur le serveur LWS
# Adaptez ce chemin selon votre configuration LWS
PROJET_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJET_PATH)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'childrensfruit.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
