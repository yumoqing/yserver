import re
import base64
import json
from traceback import format_exc
from aiohttp import web
from appPublic.dictObject import DictObject
from appPublic.log import debug, info, exception, error
from appPublic.httpclient import HttpClient, RESPONSE_TEXT, RESPONSE_JSON, RESPONSE_BIN,RESPONSE_FILE, RESPONSE_STREAM
from appPublic.registerfunction import RegisterFunction
from appPublic.argsConvert import ArgsConvert

def encode_imagefile(fn):
	with open(fn, 'rb') as f:
		return base64.b64encode(f.read()).decode('utf-8')

class StreamLlmProxy:
	def __init__(self, processor, desc):
		assert desc.name
		self.name = desc.name
		self.processor = processor
		self.auth_api = desc.auth
		self.desc = desc
		self.api_name = desc.name
		self.data = DictObject()
		self.ac = ArgsConvert('${', '}')
	
	def line_chunk_match(self, l):
		if self.api.chunk_match:
			match = re.search(self.api.chunk_match, l)
			if match:
				return match.group(1)
		return l

	async def write_chunk(self, ll):
		def eq(a, b):
			return a == b
		def ne(a, b):
			return a != b
		opfuncs = {
			'==':eq,
			'!=':ne
		}
		if '[DONE]' in ll:
			return
		try:
			# print('write_chunk(),l=', ll)
			l = self.line_chunk_match(ll)
			d = DictObject(** json.loads(l))
			j = {}
			for r in self.api.resp or []:
				j[r.name] = d.get_data_by_keys(r.value);

			if self.api.chunk_filter:
				v = d.get_data_by_keys(self.api.chunk_filter.name)
				v1 = self.api.chunk_filter.value
				op = self.api.chunk_filter.op
				f = opfuncs.get(op)
				if f and f(v,v1):
					j[self.api.chunk_filter.field] = ''

			jstr = json.dumps(j) + '\n'
			bin = jstr.encode('utf-8')
			await self.resp.write(bin)
			await self.resp.drain()
		except Exception as e:
			tb = format_exc()
			exception(f'Error:Write_chunk(),{l=} error:{e=}{tb}')

	async def stream_handle(self, chunk):
		print('chunk=', chunk)
		chunk = chunk.decode('utf-8')
		chunk = self.remain_str + chunk
		lines = chunk.split('\n')
		self.remain_str = lines[-1]
		ls = lines[:-1]
		for l in ls:	
			if l == '':
				continue
			await self.write_chunk(l)

	async def get_apikey(self, apiname):
		f = self.processor.run_ns.get_llm_user_apikey
		if f:
			# return a DictObject instance
			return await f(apiname, self.user)
		raise Exception('get_llm_user_apikey() function not found in ServerEnv')

	async def get_apidata(self, parts, params={}):
		ret = {}
		for d in parts or []:
			v = d['value']
			if params != {}:
				v = self.datalize(v, params)
			if d.get('convertor'):
				rf = RegisterFunction()
				v = await rf.exe(d['convertor'], v)
			ret[d['name']] = v
		return ret
			
	async def do_auth(self, request):
		d = self.desc.auth
		self.data = self.get_data(self.name)
		if self.data.authed:
			return
		self.data = await self.get_apikey(self.name)
		if self.data is None:
			raise Exception(f'user({self.user}) do not has a apikey for {self.name}')
		params = self.data
		method = d.get('method', 'POST')
		_headers = self.get_apidata(d.get('headers', []), params)
		_data = self.get_apidata(d.get('data', []), params)
		_params = self.get_apidata(d.get('params',[]), params)
		url = d.get('url')
		hc = HttpClient()
		resp_data = await hc.request(url, method, response_type=RESPONSE_JSON,
								params=_params,
								data=None if _data == {} else json.dumps(_data),
								headers=_headers)
		resp_data = DictObject(**resp_data)
		for sd in d.set_data:
			self.data[sd.name] = resp_data.get_data_by_keys(sd.field)
		self.data.authed = True
		self.set_data(self.name, self.data)

	def data_key(self, apiname):
		if self.user is None:
			self.user = 'anonymous'
		return apiname + '_a_' + self.user

	def set_data(self, apiname, data):
		request = self.processor.run_ns.request
		app = request.app
		app.set_data(self.data_key(apiname), data)
	
	def get_data(self, apiname):
		request = self.processor.run_ns.request
		app = request.app
		return app.get_data(self.data_key(apiname))
		
	async def __call__(self, request, params):
		self.user = await self.processor.run_ns.get_user()
		mapi = params.mapi
		stream = params.stream
		self.resp = web.StreamResponse()
		await self.resp.prepare(request)
		if stream is None:
			stream = True
		self.remain_str = ''
		if not self.desc[mapi]:
			raise Exception(f'{mapi} not defined')
		d = self.desc[mapi]
		self.api = d
		self.chunk_match = d.chunk_match
		if self.api.need_auth and self.auth_api:
			await self.do_auth(request)
		else:
			self.data = await self.get_apikey(self.name)
			
		assert d.get('url')
		url = d.get('url')
		method = d.get('method', 'POST')
		params1 = self.data
		params1.update(params)
		params = params1
		method = d.get('method', 'POST')
		_headers = self.get_apidata(d.get('headers', []), params)
		_data = self.get_apidata(d.get('data', []), params)
		_params = self.get_apidata(d.get('params',[]), params)
		response_type =  RESPONSE_STREAM
		hc = HttpClient()
		debug(f'{url=},{method=},{_params=},{_data=},{_headers=}')
		resp_data = await hc.request(url, method, response_type=response_type,
								params=_params,
								data=None if _data == {} else json.dumps(_data),
								stream_func=self.stream_handle,
								headers=_headers)
		if self.remain_str != '':
			await self.write_chunk(self.remain_str)
		return self.resp
		
	def datalize(self, dic, data={}):
		mydata = self.data.copy()
		mydata.update(data)
		s1 = self.ac.convert(dic, mydata)
		return s1
	
class SyncLlmProxy(StreamLlmProxy):
	async def __call__(self, request, params):
		self.user = await self.processor.run_ns.get_user()
		mapi = params.mapi
		if not self.desc[mapi]:
			return {
				"status":"Error",
				"message":f'{mapi} not defined'
			}
		d = self.desc[mapi]
		self.api = d
		if self.api.need_auth and self.auth_api:
			await self.do_auth(request)
		else:
			self.data = await self.get_apikey(self.name)
			
		assert d.get('url')
		method = d.get('method', 'POST')
		url = d.get('url')
		params1 = self.data
		params1.update(params)
		params = params1
		method = d.get('method', 'POST')
		_headers = self.get_apidata(d.get('headers', []), params)
		_data = self.get_apidata(d.get('data', []), params)
		_params = self.get_apidata(d.get('params',[]), params)
		response_type =  RESPONSE_JSON
		hc = HttpClient()
		debug(f'{url=},{method=},{_params=},{_data=},{_headers=}')
		resp_data = await hc.request(url, method, response_type=response_type,
								params=_params,
								data=None if _data == {} else json.dumps(_data),
								headers=_headers)
		debug(f'{resp_data=}')
		if resp_data is None:
			return {
				"status":"Error",
				"message":f'{mapi} not defined'
			}
		resp_data = DictObject(resp_data)
		return self.convert_resp(resp_data)
		
	def convert_resp(self, resp):
		if self.api.resp is None:
			return resp
		j = {}
		for r in self.api.resp or []:
			j[r.name] = resp.get_data_by_keys(r.value);
		return j


class AsyncLlmProxy(StreamLlmProxy):
	async def __call__(self, request, params):
		self.user = await self.processor.run_ns.get_user()
		mapi = params.mapi
		stream = params.stream
		self.resp = web.StreamResponse()
		await self.resp.prepare(request)
		if stream is None:
			stream = True
		self.remain_str = ''
		if not self.desc[mapi]:
			raise Exception(f'{mapi} not defined')
		d = self.desc[mapi]
		self.api = d
		self.chunk_match = d.chunk_match
		if self.api.need_auth and self.auth_api:
			await self.do_auth(request)
		else:
			self.data = await self.get_apikey(self.name)
			
		assert d.get('url')
		url = d.get('url')
		method = d.get('method', 'POST')
		params1 = self.data
		params1.update(params)
		params = params1
		method = d.get('method', 'POST')
		_headers = self.get_apidata(d.get('headers', []), params)
		_data = self.get_apidata(d.get('data', []), params)
		_params = self.get_apidata(d.get('params',[]), params)
		response_type =  RESPONSE_JSON
		hc = HttpClient()
		debug(f'{url=},{method=},{_params=},{_data=},{_headers=}')
		resp_data = await hc.request(url, method, response_type=response_type,
								params=_params,
								data=None if _data == {} else json.dumps(_data),
								headers=_headers)
		if self.remain_str != '':
			await self.write_chunk(self.remain_str)
		return self.resp
