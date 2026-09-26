"""Trace lifecycle helpers with a conservative default."""


async def start_trace(context, screenshots=False, snapshots=True, sources=False):
    await context.tracing.start(screenshots=screenshots, snapshots=snapshots, sources=sources)


async def stop_trace(context, path):
    await context.tracing.stop(path=path)
