import os
import re
import traceback

from aiohttp.web_response import Response
from aiohttp.web_exceptions import (
    HTTPException,
    HTTPExpectationFailed,
    HTTPForbidden,
    HTTPMethodNotAllowed,
    HTTPNotFound,
)
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_routedef import AbstractRouteDef
from aiohttp.web import json_response


from sqlor.crud import CRUD

from appPublic.dictObject import multiDict2Dict
from appPublic.jsonConfig import getConfig
from appPublic.log import info, debug, warning, error, critical, exception

from .error import Error,Success
actions = [
	"browse",
	"add",
	"update",
	"filter"
]

class DBAdmin:
	def __init__(self, request,dbname,tablename, action):
		self.dbname = dbname
		self.tablename = tablename
		self.request = request
		self.action = action
		if action not in actions:
			debug('action not defined:%s' % action)
			raise HTTPNotFound
		try:
			self.crud = CRUD(dbname,tablename)
		except Exception as e:
			exception('e= %s' % e)
			traceback.print_exc()
			raise HTTPNotFound
		
	async def render(self) -> Response:
		try:
			d = await self.crud.I()
			return json_response(Success(d))
		except Exception as e:
			exception('except=%s' % e)
			traceback.print_exc()
			return json_response(Error(errno='metaerror',msg='get metadata error'))

