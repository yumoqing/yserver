from aiohttp import web
from p2psc.pubkey_handler import PubkeyHandler
from p2psc.p2psc import P2psc

class P2pLayer
	def __init__(self):
		self.p2pcrypt = False
		config = getConfig()
		if config.website.p2pcrypt:
			self.p2pcrypt = True
		if not self.p2pcrypt:
			return
		self.handler = PubkeyHandler()
		self.p2p = P2psc(self.handler, self.handler.get_myid())

	@web.middleware
	async def p2p_middle(self, request, handler):
		if not p2pscrypr:
			return await handler(request)

		if request.headers.get('P2pHandShake', None):
			resturen await self.p2p_handshake(request)

		if request.header.get('P2pdata', None):
			request = await self.p2p_decode_request(request)
			resp = await handler(request)
			return await self.p2p_encode_response(resp)

		return handler(request)

	async def p2p_handshake(self, request):
		pass

	async def p2p_decode_request(self, request):
		pass

	async def p2p_encode_response(self, response):
		return response

