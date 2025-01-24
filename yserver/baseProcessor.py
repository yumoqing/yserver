import os
import re
import json
import codecs
import aiofiles
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse

from appPublic.jsonConfig import getConfig
from appPublic.dictObject import DictObject
from appPublic.folderUtils import listFile
from appPublic.argsConvert import ArgsConvert
from appPublic.log import info, debug, warning, error, critical, exception

from .utils import unicode_escape
from .serverenv import ServerEnv
from .filetest import current_fileno

class ObjectCache:
	def __init__(self):
		self.cache = {}

	def store(self,path,obj):
		o = self.cache.get(path,None)
		if o is not None:
			try:
				del o.cached_obj
			except:
				pass
		o = DictObject()
		o.cached_obj = obj
		o.mtime = os.path.getmtime(path)
		self.cache[path] = o

	def get(self,path):
		o = self.cache.get(path)
		if o:
			if os.path.getmtime(path) > o.mtime:
				return None
			return o.cached_obj
		return None


		
class BaseProcessor:
	@classmethod
	def isMe(self,name):
		return name=='base'

	def __init__(self,path,resource):
		self.env_set = False
		self.path = path
		self.resource = resource
		self.retResponse = None
		# self.last_modified = os.path.getmtime(path)
		# self.content_length = os.path.getsize(path)
		self.headers = {
			'Content-Type': 'text/html; utf-8',
			'Accept-Ranges': 'bytes'
		}
		self.content = ''

	async def be_call(self, request, params={}):
		return await self.path_call(request, params=params)

	async def set_run_env(self, request, params={}):
		if self.env_set:
			return
		self.real_path = self.resource.url2file(request.path)
		g = ServerEnv()
		self.run_ns = DictObject()
		self.run_ns.update(g)
		self.run_ns.update(self.resource.y_env)
		self.run_ns['request'] = request
		self.run_ns['app'] = request.app
		kw = await self.run_ns['request2ns']()
		kw.update(params)
		self.run_ns['params_kw'] = kw
		# self.run_ns.update(kw)
		self.run_ns['ref_real_path'] = self.real_path
		self.run_ns['processor'] = self
		self.env_set = True

	async def execute(self,request):
		await self.set_run_env(request)
		await self.datahandle(request)
		return self.content

	def set_response_headers(self, response):
		response.headers['Access-Control-Expose-Headers'] = 'Set-Cookie'
		# response.headers['Access-Control-Allow-Credentials'] = 'true'
		# response.headers['Access-Control-Allow-Origin'] = '47.93.12.75'

	async def handle(self,request):
		await self.execute(request)
		jsonflg = False
		if self.retResponse is not None:
			self.set_response_headers(self.retResponse)
			return self.retResponse
		elif isinstance(self.content, Response):
			return self.content
		elif isinstance(self.content, StreamResponse):
			return self.content
		elif isinstance(self.content, DictObject):
			self.content = json.dumps(self.content, indent=4)
			jsonflg = True
		elif isinstance(self.content, dict):
			self.content = json.dumps(self.content, indent=4)
			jsonflg = True
		elif isinstance(self.content, list):
			self.content = json.dumps(self.content, indent=4)
			jsonflg = True
		elif isinstance(self.content, tuple):
			self.content = json.dumps(self.content, indent=4)
			jsonflg = True
		elif isinstance(self.content, bytes):
			self.headers['Access-Control-Expose-Headers'] = 'Set-Cookie'
			self.headers['Content-Length'] = str(len(self.content))
			resp =  Response(body=self.content,headers=self.headers)
			self.set_response_headers(resp)
			return resp
		else:
			try:
				json.loads(self.content)
				jsonflg = True
			except:
				pass
		
		if jsonflg:
			self.headers['Content-Type'] = "application/json; utf-8"

		self.headers['Access-Control-Expose-Headers'] = 'Set-Cookie'
		resp =  Response(text=self.content,headers=self.headers)
		self.set_response_headers(resp)
		return resp

	async def datahandle(self,request):
		debug('*******Error*************')
		self.content=''

	def setheaders(self):
		pass
		# self.headers['Content-Length'] = str(len(self.content))

class TemplateProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='tmpl'

	async def path_call(self, request, params={}):
		await self.set_run_env(request, params=params)
		path = request.path
		ns = self.run_ns
		te = self.run_ns['tmpl_engine']
		return await te.render(path,**ns)

	async def datahandle(self,request):
		self.content = await self.path_call(request)
		
	def setheaders(self):
		super(TemplateProcessor,self).setheaders()
		if self.path.endswith('.tmpl.css'):
			self.headers['Content-Type'] = 'text/css; utf-8'
		elif self.path.endswith('.tmpl.js'):
			self.headers['Content-Type'] = 'application/javascript ; utf-8'
		else:
			self.headers['Content-Type'] = 'text/html; utf-8'

class BricksAppProcessor(TemplateProcessor):
	@classmethod
	def isMe(self,name):
		return name=='app'

	async def datahandle(self, request):
		params = await self.resource.y_env['request2ns']()
		await super().datahandle(request)
		if params.get('_webbricks_',None):
			return
		txt = self.content
		entire_url = self.run_ns.get('entire_url')
		content0 = await self.resource.path_call(request,entire_url('/bricks/bricksapp.tmpl'))
		ac = ArgsConvert("${", "}$")
		self.content = ac.convert(content0, {'appdic':txt})

class BricksUIProcessor(TemplateProcessor):
	@classmethod
	def isMe(self,name):
		# print(f'{name=} is a bui')
		return name=='bui'

	async def datahandle(self, request):
		params = await self.resource.y_env['request2ns']()
		await super().datahandle(request)
		if params.get('_webbricks_',None):
			return
		txt = self.content
		entire_url = self.run_ns.get('entire_url')
		content0 = await self.resource.path_call(request,entire_url('/bricks/header.tmpl'))
		content2 = await self.resource.path_call(request,entire_url('/bricks/footer.tmpl'))
		self.content = '%s%s%s' % (content0, txt, content2)

class PythonScriptProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='dspy'

	async def loadScript(self, path):
		data = ''
		async with aiofiles.open(path,'r', encoding='utf-8') as f:
			data = await f.read()
		b= ''.join(data.split('\r'))
		lines = b.split('\n')
		lines = ['\t' + l for l in lines ]
		txt = "async def myfunc(request,**ns):\n" + '\n'.join(lines)
		return txt
		
	async def path_call(self, request,params={}):
		await self.set_run_env(request, params=params)
		lenv = self.run_ns
		del lenv['request']
		txt = await self.loadScript(self.real_path)
		# print(self.real_path, "#########", txt)
		exec(txt,lenv,lenv)
		func = lenv['myfunc']
		return await func(request,**lenv)

	async def datahandle(self,request):
		self.content = await self.path_call(request)

class MarkdownProcessor(BaseProcessor):
	@classmethod
	def isMe(self,name):
		return name=='md'

	async def datahandle(self,request:Request):
		data = ''
		async with aiofiles.open(self.real_path,'r',encoding='utf-8') as f:
			data = await f.read()
			self.content = self.urlreplace(data, request)

	def urlreplace(self,mdtxt,request):
		p = '\[(.*)\]\((.*)\)'
		return re.sub(p,
				lambda x:'['+x.group(1)+'](' + self.resource.entireUrl(request, x.group(2)) + ')',
				mdtxt)

def getProcessor(name):
	# print(f'getProcessor({name})')
	return _getProcessor(BaseProcessor, name)
	
def _getProcessor(kclass,name):
	for k in kclass.__subclasses__():
		if not hasattr(k,'isMe'):
			continue
		if k.isMe(name):
			return k
		a = _getProcessor(k,name)
		if a is not None:
			return a
	return None
