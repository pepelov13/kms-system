from django.apps import AppConfig
from django.db.backends.signals import connection_created


class AssessmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assessments'

    def ready(self):
        # Connect signal to enable foreign keys in SQLite
        def activate_foreign_keys(sender, connection, **kwargs):
            if connection.vendor == 'sqlite':
                cursor = connection.cursor()
                cursor.execute('PRAGMA foreign_keys = ON;')
                cursor.close()

        connection_created.connect(activate_foreign_keys)
