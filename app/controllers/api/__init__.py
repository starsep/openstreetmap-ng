from fastapi import APIRouter

import app.controllers.api.capabilities as capabilities
import app.controllers.api.v06 as v06
import app.controllers.api.web as web

router = APIRouter()
router.include_router(v06.router)
router.include_router(web.router)  # TODO:
router.include_router(capabilities.router)