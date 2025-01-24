import os
import re
import codecs
import aiofiles
from traceback import print_exc
# from showcallstack import showcallstack

import asyncio
import json

from yarl import URL

from aiohttp import client
from aiohttp_auth import auth
from appPublic.http_client import Http_Client
from functools import partial
from aiohttp_auth import auth
from aiohttp.web_urldispatcher import StaticResource, PathLike
from aiohttp.web_urldispatcher import Optional, _ExpectHandler
from aiohttp.web_urldispatcher import Path
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_exceptions import (
	HTTPException,
	HTTPExpectationFailed,
	HTTPForbidden,
	HTTPMethodNotAllowed,
	HTTPNotFound,
	HTTPFound,
)
from aiohttp.web_fileresponse import FileResponse
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_routedef import AbstractRouteDef

from appPublic.jsonConfig import getConfig
from appPublic.dictObject import DictObject
from appPublic.i18n import getI18N
from appPublic.dictObject import DictObject, multiDict2Dict
from appPublic.timecost import TimeCost
from appPublic.timeUtils import timestampstr
from appPublic.log import clientinfo, info, debug, warning, error, critical, exception

from .baseProcessor import getProcessor, BricksUIProcessor, TemplateProcessor
from .baseProcessor import PythonScriptProcessor, MarkdownProcessor

from .xlsxdsProcessor import XLSXDataSourceProcessor
from .llmProcessor import LlmProcessor, LlmSProcessor, LlmAProcessor
from .websocketProcessor import WebsocketProcessor, XtermProcessor
from .sqldsProcessor import SQLDataSourceProcessor
from .functionProcessor import FunctionProcessor
from .proxyProcessor import ProxyProcessor
from .serverenv import ServerEnv
from .url2file import Url2File
from .filestorage import FileStorage, file_realpath
from .restful import DBCrud
from .dbadmin import DBAdmin
from .filedownload import file_download, path_decode
from .utils import unicode_escape
from .filetest import current_fileno
from .auth_api import user_login, user_logout, get_session_user, get_session_userinfo

def getHeaderLang(request):
	al = request.headers.get('Accept-Language')
	if al is None:
		return 'en'
	return al.split(',')[0]
	
def i18nDICT(request):
	c = getConfig()
	i18n = getI18N()
	lang = getHeaderLang(request)
	l = c.langMapping.get(lang,lang)
	return json.dumps(i18n.getLangDict(l)).encode(c.website.coding)


class ProcessorResource(StaticResource,Url2File):
	def __init__(self, prefix: str, directory: PathLike,
				 *, name: Optional[str]=None,
				 expect_handler: Optional[_ExpectHandler]=None,
				 chunk_size: int=256 * 1024,
				 show_index: bool=False, follow_symlinks: bool=False,
				 append_version: bool=False,
				 indexes:list=[],
				 processors:dict={}) -> None:
		StaticResource.__init__(self,prefix, directory,
				 name=name,
				 expect_handler=expect_handler,
				 chunk_size=chunk_size,
				 show_index=show_index, 
				 follow_symlinks=follow_symlinks,
				 append_version=append_version)
		Url2File.__init__(self,directory,prefix,indexes,inherit=True)
		gr = self._routes.get('GET')
		self._routes.update({'POST':gr})
		self._routes.update({'PUT':gr})
		self._routes.update({'OPTIONS':gr})
		self._routes.update({'DELETE':gr})
		self._routes.update({'TRACE':gr})
		self.y_processors = processors
		self.y_prefix = prefix
		self.y_directory = directory
		self.y_indexes = indexes
		self.y_env = DictObject()
		
	def setProcessors(self, processors):
		self.y_processors = processors

	def setIndexes(self, indexes):
		self.y_indexes = indexes

	
	def abspath(self, request, path:str):
		url =  self.entireUrl(request, path)
		path = self.url2path(url)
		fname = self.url2file(path)
		return fname

	async def getPostData(self,request: Request) -> DictObject:
		qd = {}
		if request.query:
			qd = multiDict2Dict(request.query)
		reader = None
		try:
			reader = await request.multipart()
		except:
			# print('reader is None')
			pass
		if reader is None:
			pd = await request.post()
			pd = multiDict2Dict(pd)
			if pd == {}:
				if request.can_read_body:
					x = await request.read()
					try:
						pd = json.loads(x)
					except:
						# print('body is not a json')
						pass
			qd.update(pd)
			return DictObject(**qd)
		ns = qd
		while 1:
			try:
				field = await reader.next()
				if not field:
					break
				value = ''
				if hasattr(field,'filename') and field.filename is not None:
					saver = FileStorage()
					userid = await get_session_user(request)
					value = await saver.save(field.filename,field.read_chunk, userid=userid)
				else:
					value = await field.read(decode=True)
					value = value.decode('utf-8')
				ov = ns.get(field.name)
				if ov:
					if type(ov) == type([]):
						ov.append(value)
					else:
						ov = [ov,value]
				else:
					ov = value
				ns.update({field.name:ov})
				# print(f'getPostData():{ns=}')
			except Exception as e:
				print(e)
				print_exc()
				print('-----------except out ------------')
				break;
		return DictObject(ns)

	def parse_request(self, request):
		"""
		get real schema, host, port, prepath
		and save it to self._{attr}

		"""
		self._scheme = request.scheme

		self._scheme = request.headers.get('X-Forwarded-Scheme',request.scheme)
		k = request.host.split(':')
		host = k[0]
		port = 80
		if len(k) == 2:
			port = int(k[1])
		elif self._scheme.lower() == 'https':
			port = 443
	
		self._host = request.headers.get('X-Forwarded-Host', host)
		self._port = request.headers.get('X-Forwarded-Port', port)
		self._prepath = request.headers.get('X-Forwarded-Prepath', '')
		if self._prepath != '':
			self._prepath = '/' + self._prepath

		self._preurl = f'{self._scheme}://{self._host}:{self._port}{self._prepath}'
		# print(f'{request.path=}, {self._preurl=}')


	async def _handle(self,request:Request) -> StreamResponse:
		clientkeys = {
			"iPhone":"iphone",
			"iPad":"ipad",
			"Android":"androidpad",
			"Windows Phone":"winphone",
			"Windows NT[.]*Win64; x64":"pc",
		}

		def i18nDICT():
			c = getConfig()
			g = ServerEnv()
			if not g.get('myi18n',False):
				g.myi18n = getI18N()
			lang = getHeaderLang(request)
			l = c.langMapping.get(lang,lang)
			return json.dumps(g.myi18n.getLangDict(l))

		def getClientType(request):
			agent = request.headers.get('user-agent')
			if type(agent)!=type('') and type(agent)!=type(b''):
				return 'pc'
			for k in clientkeys.keys():
				m = re.findall(k,agent)
				if len(m)>0:
					return clientkeys[k]
			return 'pc'

		def serveri18n(s):
			lang = getHeaderLang(request)
			c = getConfig()
			g = ServerEnv()
			if not g.get('myi18n',False):
				g.myi18n = getI18N()
			l = c.langMapping.get(lang,lang)
			return g.myi18n(s,l)

			
		async def getArgs() -> DictObject:
			if request.method == 'POST':
				return await self.getPostData(request)
			ns = multiDict2Dict(request.query)
			return DictObject(**ns)

		async def redirect(url):
			url = self.entireUrl(request, url)
			raise HTTPFound(url)

		async def remember_user(userid, 
							username='',
							userorgid=''):
			await user_login(request, userid,
							username=username,
							userorgid=userorgid)
		
		async def remember_ticket(ticket):
			await auth.remember_ticket(request, ticket)

		async def get_ticket():
			return await auth.get_ticket(request)

		async def forget_user():
			await user_logout(request)

		async def get_username():
			info = await get_session_userinfo(request)
			return info.username

		async def get_userinfo():
			info = await get_session_userinfo(request)
			return info

		async def get_userorgid():
			info = await get_session_userinfo(request)
			return info.userorgid

		async def get_user():
			return await get_session_user(request)

		self.parse_request(request)

		self.y_env.i18n = serveri18n
		self.y_env.file_realpath = file_realpath
		self.y_env.redirect = redirect
		self.y_env.info = info
		self.y_env.error = error
		self.y_env.debug = debug
		self.y_env.clientinfo = clientinfo
		self.y_env.warning = warning
		self.y_env.critical = critical
		self.y_env.exception = exception
		self.y_env.remember_user = remember_user
		self.y_env.forget_user = forget_user
		self.y_env.get_user = get_user
		self.y_env.get_username = get_username
		self.y_env.get_userorgid = get_userorgid
		self.y_env.get_userinfo = get_userinfo
		self.y_env.i18nDict = i18nDICT
		self.y_env.terminalType = getClientType(request)
		self.y_env.entire_url = partial(self.entireUrl,request)
		self.y_env.websocket_url = partial(self.websocketUrl,request)
		self.y_env.abspath = self.abspath
		self.y_env.request2ns = getArgs
		self.y_env.aiohttp_client = client
		self.y_env.resource = self
		self.y_env.gethost = partial(self.gethost, request)
		self.y_env.path_call = partial(self.path_call,request)
		self.user = await auth.get_auth(request)
		self.y_env.user = self.user
		self.request_filename = self.url2file(str(request.path))
		request['request_filename'] = self.request_filename
		path = request.path
		config = getConfig()
		request['port'] = config.website.port
		if config.website.dbadm and path.startswith(config.website.dbadm):
			pp = path.split('/')[2:]
			if len(pp)<3:
				error('%s:not found' % str(request.url))
				raise HTTPNotFound
			dbname = pp[0]
			tablename = pp[1]
			action = pp[2]
			adm = DBAdmin(request,dbname,tablename,action)
			return await adm.render()
		if config.website.dbrest and path.startswith(config.website.dbrest):
			pp = path.split('/')[2:]
			if len(pp)<2:
				error('%s:not found' % str(request.url))
				raise HTTPNotFound
			dbname = pp[0]
			tablename = pp[1]
			id = None
			if len(pp) > 2:
				id = pp[2]
			crud = DBCrud(request,dbname,tablename,id=id)
			return await crud.dispatch()
		if config.website.download and path.startswith(config.website.download):
			pp = path.split('/')[2:]
			if len(pp)<1:
				error('%s:not found' % str(request.url))
				raise HTTPNotFound
			dp = '/'.join(pp)
			path = path_decode(dp)
			return await file_download(request, path)

		processor = self.url2processor(request, str(request.url), self.request_filename)
		if processor:
			ret = await processor.handle(request)
			return ret

		if self.request_filename and await self.isHtml(self.request_filename):
			return await self.html_handle(request, self.request_filename)

		if self.request_filename and os.path.isdir(self.request_filename):
			config = getConfig()
			if not config.website.allowListFolder:
				error('%s:not found' % str(request.url))
				raise HTTPNotFound
		# print(f'{self.request_filename=}, {str(request.url)=} handle as a normal file')
		return await super()._handle(request)

	def gethost(self, request):
		host = request.headers.get('X-Forwarded-Host')
		if host:
			return host
		host = request.headers.get('Host')
		if host:
			return host
		return '/'.join(str(request.url).split('/')[:3])
		
	async def html_handle(self,request,filepath):
		async with aiofiles.open(filepath,'r', encoding='utf-8') as f:
			txt = await f.read()
			utxt = txt.encode('utf-8')
			headers = {
				'Content-Type': 'text/html; utf-8',
				'Accept-Ranges': 'bytes',
				'Content-Length': str(len(utxt))
			}
			resp = Response(text=txt,headers=headers)
			return resp
			
	async def isHtml(self,fn):
		try:
			async with aiofiles.open(fn,'r',encoding='utf-8') as f:
				b = await f.read()
				while b[0] in ['\n',' ','\t']:
					b = b[1:]
				if b.lower().startswith('<html>'):
					return True
				if b.lower().startswith('<!doctype html>'):
					return True
		except Exception as e:
			return False
		
	def url2processor(self, request, url, fpath):
		config = getConfig()
		url1 = url
		url = self.entireUrl(request, url)
		host =  '/'.join(url.split('/')[:3])
		path = '/' + '/'.join(url.split('/')[3:])
		if config.website.startswiths:
			for a in config.website.startswiths:
				leading = self.entireUrl(request, a.leading)
				if path.startswith(a.leading):
					processor = FunctionProcessor(path,self,a)
					return processor

		if fpath is None:
			print(f'fpath is None ..., {url=}, {url1=}')
			return None
		for word, handlername in self.y_processors:
			if fpath.endswith(word):
				Klass = getProcessor(handlername)
				try:
					processor = Klass(path,self)
					# print(f'{f_cnt1=}, {f_cnt2=}, {f_cnt3=}, {f_cnt4=}, {f_cnt5=}')
					return processor
				except Exception as e:
					print('Exception:',e, 'handlername=', handlername)
					return None
		return None

	def websocketUrl(self, request, url):
		
		url = self.entireUrl(request, url)
		if url.startswith('https'):
			return 'wss' + url[5:]
		return 'ws' + url[4:]

	def urlWebsocketify(self, url):
		if url.endswith('.ws') or url.endswith('.wss'):
			if url.startswith('https'):
				return 'wss' + url[5:]
			return 'ws' + url[4:]
		return url

	def entireUrl(self, request, url):
		ret_url = ''
		if url.startswith('http://') or \
					url.startswith('https://') or \
					url.startswith('ws://') or \
					url.startswith('wss://'):
			ret_url = url
		elif url.startswith('/'):
			u =  f'{self._preurl}{url}'
			# print(f'entireUrl(), {u=}, {url=}, {self._preurl=}')
			ret_url = u
		else:
			path = request.path
			p = self.relatedurl(path,url)
			u = f'{self._preurl}{p}'
			ret_url = u
		return self.urlWebsocketify(ret_url)

	def url2path(self, url):
		if url.startswith(self._preurl):
			return url[len(self._preurl):]
		return url

	async def path_call(self, request, path, params={}):
		url = self.entireUrl(request, path)
		# print(f'{path=}, after entireUrl(), {url=}')
		path = self.url2path(url)
		fpath = self.url2file(path)
		processor = self.url2processor(request, path, fpath)
		# print(f'path_call(), {path=}, {url=}, {fpath=}, {processor=}, {self._prepath}')
		new_request = request.clone(rel_url=path)
		return await processor.be_call(new_request, params=params)
		
