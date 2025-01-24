import os
import codecs

from appPublic.Singleton import SingletonDecorator
from appPublic.jsonConfig import getConfig

from jinja2 import Template,Environment, BaseLoader
from .serverenv import ServerEnv
from .url2file import Url2File, TmplUrl2File

class TmplLoader(BaseLoader, TmplUrl2File):
	def __init__(self, paths, indexes, subffixes=['.tmpl'], inherit=False):
		BaseLoader.__init__(self)
		TmplUrl2File.__init__(self,paths,indexes=indexes,subffixes=subffixes, inherit=inherit)
	
	def get_source(self,env: Environment,template: str):
		config = getConfig()
		coding = config.website.coding

		fp = self.url2file(template)
		# print(f'{template=} can not transfer to filename')
		if not os.path.isfile(fp):
			raise TemplateNotFound(template)
		mtime = os.path.getmtime(fp)
		with codecs.open(fp,'r',coding) as f:
			source =  f.read()
		return source,fp,lambda:mtime == os.path.getmtime(fp)

	def join_path(self,name, parent):
		return self.relatedurl(parent,name)

	def list_templates(self):
		return []


class TemplateEngine(Environment):
	def __init__(self,loader=None):
		Environment.__init__(self,loader=loader, enable_async=True)
		self.urlpaths = {}
		self.loader = loader
	
	def join_path(self,template: str, parent: str):
		return self.loader.join_path(template, parent)

	async def render(self,___name: str, **globals):
		t = self.get_template(___name,globals=globals)
		return await t.render_async(globals)

def setupTemplateEngine():
	config = getConfig()
	subffixes = [ i[0] for i in config.website.processors if i[1] == 'tmpl' ]
	loader = TmplLoader(config.website.paths,
				config.website.indexes,
				subffixes,
				inherit=True)
	engine = TemplateEngine(loader)
	g = ServerEnv()
	g.tmpl_engine = engine

