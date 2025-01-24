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
from aiohttp.web import json_response


from sqlor.dbpools import DBPools

from appPublic.dictObject import multiDict2Dict
from appPublic.jsonConfig import getConfig

from .error import Error,Success

DEFAULT_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE')

class RestEndpoint:

	def __init__(self):
		self.methods = {}

		for method_name in DEFAULT_METHODS:
			method = getattr(self, method_name.lower(), None)
			if method:
				self.register_method(method_name, method)

	def register_method(self, method_name, method):
		self.methods[method_name.upper()] = method

	async def dispatch(self):
		method = self.methods.get(self.request.method.lower())
		if not method:
			raise HTTPMethodNotAllowed('', DEFAULT_METHODS)

		return await method()


class DBCrud(RestEndpoint):
	def __init__(self, request,dbname,tablename, id=None):
		super().__init__()
		self.dbname = dbname
		self.tablename = tablename
		self.request = request
		self.db = DBPools()
		self.id = id
		
	async def options(self) -> Response:
		try:
			with self.db.sqlorContext(self.dbname) as sor:
				d = await sor.I(self.tablename)
				return json_response(Success(d))
		except Exception as e:
			print(e)
			traceback.print_exc()
			return json_response(Error(errno='metaerror',msg='get metadata error'))

	async def get(self) -> Response:
		"""
		query data
		"""
		try:
			ns = multiDict2Dict(self.request.query)
			with self.db.sqlorContext(self.dbname) as sor:
				d = await sor.R(self.tablename, ns)
				return json_response(Success(d))
		except Exception as e:
			print(e)
			traceback.print_exc()
			return json_response(Error(errno='search error',msg='search error'))

	async def post(self):
		"""
		insert data
		"""
		try:
			ns = multiDict2Dict(await self.request.post())
			with self.db.sqlorContext(self.dbname) as sor:
				d = await sor.C(self.tablename, ns)
				return json_response(Success(d))
		except Exception as e:
			print(e)
			traceback.print_exc()
			return json_response(Error(errno='add error',msg='add error')) 

	async def put(self):
		"""
		update data
		"""
		try:
			ns = multiDict2Dict(await self.request.post())
			with self.db.sqlorContext(self.dbname) as sor:
				d = await sor.U(self.tablename, ns)
				return json_response(Success(' '))
		except Exception as e:
			print(e)
			traceback.print_exc()
			return json_response(Error(errno='update error',msg='update error'))
		
	async def delete(self, request: Request, instance_id):
		"""
		delete data
		"""
		try:
			ns = multiDict2Dict(self.request.query)
			with self.db.sqlorContext(self.dbname) as sor:
				d = await sor.D(self.tablename, ns)
				return json_response(Success(d))
		except Exception as e:
			print(e)
			traceback.print_exc()
			return json_response(Error(erron='delete error',msg='error'))
