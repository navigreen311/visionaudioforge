from celery import Celery

from app.config import settings

celery_app = Celery(
    "visionaudioforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    # Without `include` the worker starts with an empty task registry: it
    # connects to the broker, answers `inspect ping`, and then rejects every
    # message it is handed with
    #
    #   Received unregistered task of type 'run_pipeline_task'. KeyError
    #
    # Nothing imported app.tasks and there was no autodiscover_tasks() call, so
    # the decorators that register these tasks never ran inside the worker
    # process; `inspect registered` reported "- empty -". Celery imports these
    # modules lazily at worker start, which is why this does not create the
    # circular import a module-level import here would.
    include=[
        "app.tasks.pipeline",
        "app.tasks.training",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
