from contextlib import contextmanager
import restate
import uuid
import sys

@contextmanager
def deterministic_uuid(ctx: restate.ObjectContext):
    # Store original functions
    original_uuid4 = uuid.uuid4

    # Monkey patch the uuid module itself
    def deterministic_uuid():
        new_id = ctx.uuid()
        print("another patched id not from event " + str(new_id))
        return new_id
    uuid.uuid4 = deterministic_uuid

    # Also patch any modules that might have already imported uuid.uuid4
    modules_to_patch = []
    for module_name, module in sys.modules.items():
        if module and hasattr(module, 'uuid') and hasattr(module.uuid, 'uuid4'):
            modules_to_patch.append((module, module.uuid.uuid4))
            module.uuid.uuid4 = deterministic_uuid

    try:
        yield
    finally:
        # Restore original functions
        uuid.uuid4 = original_uuid4
        for module, original_func in modules_to_patch:
            module.uuid.uuid4 = original_func