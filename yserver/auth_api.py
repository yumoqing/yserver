import time
import uuid
from traceback import format_exc
from aiohttp_auth import auth
from aiohttp_auth.auth.ticket_auth import TktAuthentication
from aiohttp_session.redis_storage import RedisStorage
from os import urandom
from aiohttp import web
import aiohttp_session
import aioredis
import base64
import binascii

from aiohttp_session import get_session, session_middleware, Session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session.redis_storage import RedisStorage

from appPublic.jsonConfig import getConfig
from appPublic.dictObject import DictObject
from appPublic.rsawrap import RSA
from appPublic.log import info, debug, warning, error, critical, exception

def get_client_ip(obj, request):
	ip = request.headers.get('X-Forwarded-For')
	if not ip:
		ip = request.remote
	request['client_ip'] = ip
	return ip

async def get_session_userinfo(request):
	d = await auth.get_auth(request)
	if d is None:
		return DictObject()
	ui = d.split(':')
	return DictObject(**{
		'userid':ui[0],
		'username':ui[1],
		'userorgid':ui[2]
	})
	
async def get_session_user(request):
	userinfo = await get_session_userinfo(request)
	return userinfo.userid

async def user_login(request, userid, username='', userorgid=''):
	ui = f'{userid}:{username}:{userorgid}'
	await auth.remember(request, ui)

async def user_logout(request):
	await auth.forget(request)

class MyRedisStorage(RedisStorage):
	def key_gen(self, request):
		key = request.headers.get('client_uuid')
		if not key:
			key = uuid.uuid4().hex
			return key
		if isinstance(key, str):
			key = key.encode('utf-8')
		key = binascii.hexlify(key)
		key = key.decode('utf-8')
		return key
		
	async def save_session(self, request: web.Request, 
				response: web.StreamResponse, 
				session: Session) -> None:
		key = session.identity
		if key is None:
			key = self.key_gen(request)
			self.save_cookie(response, key, max_age=session.max_age)
		else:
			if session.empty:
				self.save_cookie(response, "", max_age=session.max_age)
			else:
				key = str(key)
				self.save_cookie(response, key, max_age=session.max_age)

		data_str = self._encoder(self._get_session_data(session))
		await self._redis.set(
			self.cookie_name + "_" + key,
			data_str,
			ex=session.max_age,
		)

class AuthAPI:
	def __init__(self):
		self.conf = getConfig()

	async def checkUserPermission(self, request, user, path):
		# print('************* checkUserPermission() use default one ****************')
		return True

	def getPrivateKey(self):
		if not hasattr(self,'rsaEngine'):
			self.rsaEngine = RSA()
			fname = self.conf.website.rsakey.privatekey
			self.privatekey = self.rsaEngine.read_privatekey(fname)
		return self.privatekey

	def rsaDecode(self,cdata):
		self.getPrivateKey()
		return self.rsaEngine.decode(self.privatekey,cdata)

	async def setupAuth(self,app):
		# setup session middleware in aiohttp fashion
		b = str(self.conf.website.port).encode('utf-8')
		cnt = 32 - len(b)
		secret = b + b'iqwertyuiopasdfghjklzxcvbnm12345'[:cnt]
		storage = EncryptedCookieStorage(secret)
		if self.conf.website.session_redis:
			url = self.conf.website.session_redis.url
			# redis = await aioredis.from_url("redis://127.0.0.1:6379")
			redis = await aioredis.from_url(url)
			storage = MyRedisStorage(redis)
		aiohttp_session.setup(app, storage)

		# Create an auth ticket mechanism that expires after 1 minute (60
		# seconds), and has a randomly generated secret. Also includes the
		# optional inclusion of the users IP address in the hash
		session_max_time = 120
		session_reissue_time = 30
		if self.conf.website.session_max_time:
			session_max_time = self.conf.website.session_max_time
		if self.conf.website.session_reissue_time:
			session_reissue_time = self.conf.website.session_reissue_time
		
		def _new_ticket(self, request, user_id):
			client_uuid = request.headers.get('client_uuid')
			ip = self._get_ip(request)
			valid_until = int(time.time()) + self._max_age
			# print(f'hack: my _new_ticket() called ... remote {ip=}, {client_uuid=}')
			return self._ticket.new(user_id, 
							valid_until=valid_until, 
							client_ip=ip, 
							user_data=client_uuid)

		TktAuthentication._get_ip = get_client_ip
		TktAuthentication._new_ticket = _new_ticket
		policy = auth.SessionTktAuthentication(secret, 
										session_max_time,
										reissue_time=session_reissue_time,
									   include_ip=True)

		# setup aiohttp_auth.auth middleware in aiohttp fashion
		# print('policy = ', policy)
		auth.setup(app, policy)
		app.middlewares.append(self.checkAuth)

	@web.middleware
	async def checkAuth(self,request,handler):
		info(f'checkAuth() called ... {request.path=}')
		t1 = time.time()
		path = request.path
		userinfo = await get_session_userinfo(request)
		user = userinfo.userid
		is_ok = await self.checkUserPermission(request, user, path)
		t2 = time.time()
		ip = get_client_ip(None, request)
		if is_ok:
			try:
				ret = await handler(request)
				t3 = time.time()
				info(f'timecost=client({ip}) {user} access {path} cost {t3-t1}, ({t2-t1})')
				return ret
			except Exception as e:
				t3 = time.time()
				tb = format_exc()
				exception(f'Exception=client({ip}) {user} access {path} cost {t3-t1}, ({t2-t1}), except={e}\n{tb}')
				raise e
				
		if user is None:
			info(f'timecost=client({ip}) {user} need login to access {path} ({t2-t1})')
			raise web.HTTPUnauthorized
		info(f'timecost=client({ip}) {user} access {path} forbidden ({t2-t1})')
		raise web.HTTPForbidden()

	async def needAuth(self,path):
		return False

