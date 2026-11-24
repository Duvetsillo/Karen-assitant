"""Pump real Tk events while waiting for asynchronous test work, never fake I/O."""

import time


def pump_until(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.root.update()
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError('Tk no alcanzó el estado esperado dentro del límite de prueba.')


def wait_archive(app):
    pump_until(app, lambda: not app.archive_transition and app.visible_exchange_id >= 0
               and app.archive_read_pending is None)


def close_app(app):
    app.close()
    app.archive_worker.thread.join(2)
    if app.core_activity:
        app.core_activity.thread.join(2)
