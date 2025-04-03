import restate

seat_object = restate.VirtualObject("SeatObject")


@seat_object.handler()
async def reserve(ctx: restate.ObjectContext) -> bool:
    status = await ctx.get("status") or "AVAILABLE"

    if status == "AVAILABLE":
        ctx.set("status", "RESERVED")
        return True
    else:
        return False


@seat_object.handler()
async def unreserve(ctx: restate.ObjectContext):
    status = await ctx.get("status") or "AVAILABLE"

    if status != "SOLD":
        ctx.clear("status")


@seat_object.handler()
async def mark_as_sold(ctx: restate.ObjectContext):
    status = await ctx.get("status") or "AVAILABLE"

    if status == "RESERVED":
        ctx.set("status", "SOLD")
