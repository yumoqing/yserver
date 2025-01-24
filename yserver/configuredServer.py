import os,sys
from sys import platform
import time
import ssl
from socket import *
from aiohttp import web

from appPublic.folderUtils import ProgramPath
from appPublic.dictObject import DictObject
from appPublic.jsonConfig import getConfig
from appPublic.log import info, debug, warning, error, critical, exception
from appPublic.registerfunction import RegisterCoroutine

from sqlor.dbpools import DBPools

from .processorResource import ProcessorResource
from .auth_api import AuthAPI
from .myTE import setupTemplateEngine
from .globalEnv import initEnv
from .filestorage import TmpFileRecord
from .loadplugins import load_plugins

class AHApp(web.Application):
	def __init__(self, *args, **kw):
		kw['client_max_size'] = 1024000000
		super().__init__(*args, **kw)
		self.user_data = DictObject()
	
	def set_data(self, k, v):
		self.user_data[k] = v
	
	def get_data(self, k):
		return self.user_data.get(k)

class ConfiguredServer:
	def __init__(self, auth_klass=AuthAPI, workdir=None):
		self.auth_klass = auth_klass
		self.workdir = workdir
		if self.workdir is not None:
			pp = ProgramPath()
			config = getConfig(self.workdir,
					{'workdir':self.workdir,'ProgramPath':pp})
		else:
			config = getConfig()
		if config.databases:
			DBPools(config.databases)
		self.config = config
		initEnv()
		setupTemplateEngine()
		client_max_size = 1024 * 10240
		if config.website.client_max_size:
			client_max_size = config.website.client_max_size

		self.app = AHApp(client_max_size=client_max_size)
		load_plugins(self.workdir)
	
	async def build_app(self):
		rf = RegisterCoroutine()
		await rf.exe('ahapp_built', self.app)
		auth = self.auth_klass()
		await auth.setupAuth(self.app)
		return self.app
		
	def run(self, port=None):
		config = getConfig()
		self.configPath(config)
		a = TmpFileRecord()
		ssl_context = None
		if port is None:
			port = config.website.port or 8080
		if config.website.ssl:
			ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
			ssl_context.load_cert_chain(config.website.ssl.crtfile,
						config.website.ssl.keyfile)
		reuse_port = None
		if platform != 'win32':
			reuse_port = True
		print('reuse_port=', reuse_port)
		web.run_app(self.build_app(),host=config.website.host or '0.0.0.0',
							port=port,
							reuse_port=reuse_port,
							ssl_context=ssl_context)

	def configPath(self,config):
		for p,prefix in config.website.paths:
			res = ProcessorResource(prefix,p,show_index=True,
							follow_symlinks=True,
							indexes=config.website.indexes,
							processors=config.website.processors)
			self.app.router.register_resource(res)
	
