from typing import Annotated

from fastapi import APIRouter, Response
from pydantic import PositiveInt
from sqlalchemy.orm import joinedload
from starlette import status
from starlette.responses import RedirectResponse

from app.config import API_URL
from app.lib.auth_context import web_user
from app.lib.options_context import options_context
from app.lib.render_response import render_response
from app.models.db.trace_ import Trace
from app.models.db.user import User
from app.queries.trace_query import TraceQuery
from app.queries.trace_segment_query import TraceSegmentQuery
from app.utils import json_encodes

# TODO: legacy traces url: user profiles
router = APIRouter(prefix='/trace')


@router.get('/upload')
async def upload(_: Annotated[User, web_user()]):
    return render_response('traces/upload.jinja2')


@router.get('/{trace_id:int}')
async def details(trace_id: PositiveInt):
    with options_context(joinedload(Trace.user)):
        trace = await TraceQuery.get_one_by_id(trace_id)
    await TraceSegmentQuery.resolve_coords((trace,), limit_per_trace=500, resolution=None)
    trace_coords = json_encodes(trace.coords)
    return render_response('traces/details.jinja2', {'trace': trace, 'trace_coords': trace_coords})


@router.get('/{trace_id:int}/edit')
async def edit(trace_id: PositiveInt, user: Annotated[User, web_user()]):
    with options_context(joinedload(Trace.user)):
        trace = await TraceQuery.get_one_by_id(trace_id)
    if trace.user_id != user.id:
        # TODO: this could be nicer?
        return Response(None, status.HTTP_403_FORBIDDEN)
    await TraceSegmentQuery.resolve_coords((trace,), limit_per_trace=500, resolution=None)
    trace_coords = json_encodes(trace.coords)
    return render_response('traces/edit.jinja2', {'trace': trace, 'trace_coords': trace_coords})


@router.get('/{trace_id:int}/data')
async def legacy_data(trace_id: PositiveInt):
    return RedirectResponse(f'{API_URL}/api/0.6/gpx/{trace_id}/data.gpx', status.HTTP_302_FOUND)
