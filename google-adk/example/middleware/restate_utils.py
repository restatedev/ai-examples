import uuid
import restate

from contextlib import contextmanager


@contextmanager
def restate_overrides(ctx: restate.ObjectContext):
    """Context manager to safely override global functions with Restate versions."""
    original_uuid4 = uuid.uuid4

    try:
        uuid.uuid4 = ctx.uuid
        yield
    finally:
        uuid.uuid4 = original_uuid4
