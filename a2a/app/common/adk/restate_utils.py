import restate

import contextvars
from contextlib import contextmanager, ExitStack

_restate_context = contextvars.ContextVar[restate.Context]("restate_context")


@contextmanager
def with_restate_context(ctx: restate.Context):
    """Context manager to set and reset the Restate context variable."""
    token = _restate_context.set(ctx)
    try:
        yield
    finally:
        _restate_context.reset(token)


def current_restate_context() -> restate.Context:
    """Get the current Restate context from the context variable."""
    ctx = _restate_context.get()
    if not ctx:
        raise RuntimeError("No Restate context is set in the current context.")
    return ctx


@contextmanager
def unwrap_terminal_errors():
    """Context manager to unwrap TerminalError exceptions."""
    try:
        yield
    except BaseException as e:
        # traverse the cause chain to find the root cause
        root_cause = e
        while root_cause is not None:
            if isinstance(root_cause, restate.SdkInternalBaseException):
                raise root_cause
            elif isinstance(root_cause, restate.TerminalError):
                raise root_cause
            root_cause = root_cause.__cause__
        raise


@contextmanager
def restate_overrides(ctx: restate.Context):
    """Context manager to safely override global functions with Restate versions."""
    with ExitStack() as stack:
        stack.enter_context(unwrap_terminal_errors())
        stack.enter_context(with_restate_context(ctx))
        yield