
from appPublic.Singleton import SingletonDecorator
from appPublic.dictObject import DictObject

@SingletonDecorator
class ServerEnv(DictObject):
	pass

def get_serverenv(name):
	g = ServerEnv()
	return g.get(name)

def set_serverenv(name, value):
	g = ServerEnv()
	g[name] = value

clientkeys = {
        "iPhone":"iphone",
        "iPad":"ipad",
        "Android":"androidpad",
        "Windows Phone":"winphone",
        "Windows NT[.]*Win64; x64":"pc",
}

def getClientType(request):
        agent = request.headers.get('user-agent')
        for k in clientkeys.keys():
                m = re.findall(k,agent)
                if len(m)>0:
                        return clientkeys[k]
        return 'pc'

