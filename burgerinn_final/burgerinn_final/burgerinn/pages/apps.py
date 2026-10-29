from django.apps import AppConfig


class PagesConfig(AppConfig):
    """
    Application configuration for the 'pages' app.

    Django uses this class to register the app and apply any
    app-specific configuration such as signals, checks, etc.
    """
    # Use BigAutoField as the default primary key type for models in this app
    default_auto_field = "django.db.models.BigAutoField"

    # Python path to this app – must match the app folder name
    name = "pages"
