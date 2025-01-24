import aiohttp
from aiohttp import web, BasicAuth
from aiohttp import client
from appPublic.dictObject import DictObject
from .llm_client import StreamLlmProxy, AsyncLlmProxy, SyncLlmProxy
from .baseProcessor import *

class LlmProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='llm'

	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		path = self.path
		url = self.resource.entireUrl(request, path)
		ns = self.run_ns
		ns.update(params)
		te = self.run_ns['tmpl_engine']
		txt = await te.render(url,**ns)
		data = json.loads(txt)
		return DictObject(**data)

	async def datahandle(self,request):
		chunk_size = 40960
		d = await self.path_call(request)
		llm = StreamLlmProxy(self, d)
		self.retResponse = await llm(request, self.run_ns.params_kw)

	def setheaders(self):
		pass

class LlmSProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='llms'

	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		path = self.path
		url = self.resource.entireUrl(request, path)
		ns = self.run_ns
		ns.update(params)
		te = self.run_ns['tmpl_engine']
		txt = await te.render(url,**ns)
		data = json.loads(txt)
		return DictObject(**data)

	async def datahandle(self,request):
		chunk_size = 40960
		d = await self.path_call(request)
		llm = SyncLlmProxy(self, d)
		self.content = await llm(request, self.run_ns.params_kw)

	def setheaders(self):
		pass

class LlmAProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='llma'

	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		path = self.path
		url = self.resource.entireUrl(request, path)
		ns = self.run_ns
		ns.update(params)
		te = self.run_ns['tmpl_engine']
		txt = await te.render(url,**ns)
		data = json.loads(txt)
		return DictObject(**data)

	async def datahandle(self,request):
		chunk_size = 40960
		d = await self.path_call(request)
		llm = AsyncLlmProxy(self, d)
		self.retResponse = await llm(request, self.run_ns.params_kw)

	def setheaders(self):
		pass
