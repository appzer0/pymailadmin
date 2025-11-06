# i18n/__init__.py

import os
import importlib

# Languages directory
I18N_DIR = os.path.dirname(__file__)

# Default language
DEFAULT_LANGUAGE = 'en-US'

def load_language(lang_code):
    
    try:
        module = importlib.import_module(f'i18n.{lang_code}')
        return getattr(module, 'translations', {})
    
    except ImportError:
        print(f"[i18n] Language not found: {lang_code}, fall back to {DEFAULT_LANGUAGE}")
        return load_language(DEFAULT_LANGUAGE)

def get_translations():
    lang = os.getenv('APP_LANGUAGE', DEFAULT_LANGUAGE)
    return load_language(lang)
