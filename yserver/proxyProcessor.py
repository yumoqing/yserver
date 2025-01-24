import aiohttp
from appPublic.log import info, debug, warning, error, critical, exception
from aiohttp import web, BasicAuth
from aiohttp import client
from .baseProcessor import *

class ProxyProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='proxy'

	async def path_call(self, request, params={}):
		await self.set_run_env(request)
		path = self.path
		url = self.resource.entireUrl(request, path)
		ns = self.run_ns
		ns.update(params)
		te = self.run_ns['tmpl_engine']
		txt = await te.render(url,**ns)
		data = json.loads(txt)
		debug('proxyProcessor: data=%s' % data)
		return data

	async def datahandle(self,request):
		chunk_size = 40960
		d  = await self.path_call(request)
		reqH = request.headers.copy()
		auth = None
		if d.get('user') and d.get('password'):
			auth = BasicAuth(d['user'], d['password'])
		async with client.request(
				request.method,
				d['url'],
				auth=auth,
				headers = reqH,
				allow_redirects=False,
				data=await request.read()) as res:
			headers = res.headers.copy()
			# body = await res.read()
			self.retResponse = web.StreamResponse(
					headers = headers,
					status = res.status
					# ,body=body
			)
			await self.retResponse.prepare(request)
			async for chunk in res.content.iter_chunked(chunk_size):
				await self.retResponse.write(chunk)
			debug('proxy: datahandle() finish')

		
	def setheaders(self):
		pass

