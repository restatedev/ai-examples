import uuid
import restate

from contextlib import contextmanager


@contextmanager
def restate_overrides(ctx: restate.ObjectContext):
    """Context manager to safely override global functions with Restate versions."""
    original_uuid4 = uuid.uuid4

    def restate_uuid4():
        return ctx.uuid()

    uuid.uuid4 = restate_uuid4
    try:
        yield
    finally:
        uuid.uuid4 = original_uuid4
