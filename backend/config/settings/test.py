from config.settings.base import *  # noqa: F403

DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
MEDIA_ROOT = BASE_DIR / "test_media"  # noqa: F405
