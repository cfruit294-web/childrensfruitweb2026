from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals  # noqa: F401
        _start_scheduler()


def _start_scheduler():
    import os
    import sys

    args = ' '.join(sys.argv)

    # Start only in runserver (dev) or gunicorn/uvicorn — never in
    # migrate, collectstatic, shell, etc.
    is_dev = 'runserver' in args and os.environ.get('RUN_MAIN') == 'true'
    is_server = any(cmd in args for cmd in ('gunicorn', 'uvicorn', 'daphne'))
    if not is_dev and not is_server:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from django_apscheduler.jobstores import DjangoJobStore
        import logging

        logger = logging.getLogger(__name__)

        scheduler = BackgroundScheduler(timezone='UTC')
        scheduler.add_jobstore(DjangoJobStore(), 'default')

        scheduler.add_job(
            _sync_youtube_job,
            trigger=IntervalTrigger(hours=1),
            id='sync_youtube',
            name='Sync YouTube channel',
            jobstore='default',
            replace_existing=True,
        )

        scheduler.start()
        logger.info('APScheduler démarré — sync YouTube toutes les heures.')
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f'APScheduler non démarré : {exc}')


def _sync_youtube_job():
    """Tâche planifiée : importe les nouvelles vidéos YouTube."""
    from django.conf import settings
    from django.core.management import call_command
    import logging

    logger = logging.getLogger(__name__)
    channel = getattr(settings, 'YOUTUBE_CHANNEL', '@CFRUIT24')
    api_key = getattr(settings, 'YOUTUBE_API_KEY', '')

    if not api_key:
        logger.warning('YOUTUBE_API_KEY manquant — sync YouTube ignorée.')
        return

    try:
        logger.info(f'Sync YouTube : {channel}')
        call_command('import_youtube', channel=channel, verbosity=0)
        logger.info('Sync YouTube terminée.')
    except Exception as exc:
        logger.error(f'Sync YouTube échouée : {exc}')
