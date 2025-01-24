from ahserver.configuredServer import ConfiguredServer
from ahserver.auth_api import AuthAPI

"""
need to implement your AuthAPI
class MyAuthAPI:
	def needAuth(self,path):
		return Fasle	# do not need authentication
		return True		# need authentication

	async def getPermissionNeed(self,path):
		return 'admin'

	async def checkUserPassword(self,user_id,password):
		return True
	
	async def getUserPermissions(self,user):
		return ['admin','view']
"""
if __name__ == '__main__':
	server = ConfiguredServer(AuthAPI)
	server.run()
