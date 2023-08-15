__version__ = '1.1.3'
import firebase_admin
from firebase_admin import credentials

from mpw import settings

cred = credentials.Certificate(settings.FIREBASE_CONFIG)
firebase_admin.initialize_app(cred)
try:
    default_app = firebase_admin.initialize_app(cred)
except:
    pass
