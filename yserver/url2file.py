

import os

class Url2File:
	def __init__(self,path:str,prefix: str,
					indexes: list, inherit: bool=False):
		self.rootpath = path
		self.starts = prefix
		self.indexes = indexes
		self.inherit = inherit

	def realurl(self,url:str) -> str :
		items = url.split('/')
		items = [ i for i in items if i != '.' ]
		while '..' in items:
			for i,v in enumerate(items):
				if v=='..' and i > 0:
					del items[i]
					del items[i-1]
					break
		return '/'.join(items)

	def url2ospath(self, url: str) -> str:
		url = url.split('?')[0]
		if len(url) > 0 and url[-1] == '/':
			url = url[:-1]
		paths = url.split('/')
		if url.startswith('http://') or \
					url.startswith('https://') or \
					url.startswith('ws://') or \
					url.startswith('wss://'):
			paths = paths[3:]
		f = os.path.join(self.rootpath,*paths)
		real_path = os.path.abspath(f)
		# print(f'{real_path=}, {url=}, {f=}')
		return real_path

	def url2file(self, url: str) -> str:
		ourl = url
		url = url.split('?')[0]
		real_path = self.url2ospath(url)
		if os.path.isdir(real_path):
			for idx in self.indexes:
				p = os.path.join(real_path,idx)
				if os.path.isfile(p):
					# print(f'{url=}, {real_path=}, {idx=}, {p=}')
					return p

		if os.path.isfile(real_path):
			return real_path

		if not os.path.isdir(os.path.dirname(real_path)):
			# print(f'url2file() return None, {real_path=}, {url=},{ourl=}, {self.rootpath=}')
			return None

		if not self.inherit:
			# print(f'url2file() return None, self.inherit is false, {url:}, {self.rootpath=}')
			return None

		items = url.split('/')
		if len(items) > 2:
			del items[-2]
			oldurl = url
			url = '/'.join(items)
			# print(f'{oldurl=}, {url=}')
			return self.url2file(url)
		# print(f'url2file() return None finally, {items:}, {url=}, {ourl=}, {self.rootpath=}')
		return None

	def relatedurl(self,url: str, name: str) -> str:
		if len(url) > 0 and url[-1] == '/':
			url = url[:-1]

		fp = self.url2ospath(url)
		if os.path.isfile(fp):
			items = url.split('/')
			del items[-1]
			url = '/'.join(items)
		url = url + '/' + name
		return self.realurl(url)

	def relatedurl2file(self,url: str, name: str):
		url = self.relatedurl(url,name)
		return self.url2file(url)

class TmplUrl2File:
	def __init__(self,paths,indexes, subffixes=['.tmpl','.ui' ],inherit=False):
		self.paths = paths
		self.u2fs = [ Url2File(p,prefix,indexes,inherit=inherit) \
						for p,prefix in paths ]
		self.subffixes = subffixes

	def url2file(self,url):
		for u2f in self.u2fs:
			fp = u2f.url2file(url)
			if fp:
				return fp
		return None

	def relatedurl(self,url: str, name: str) -> str:
		for u2f in self.u2fs:
			fp = u2f.relatedurl(url, name)
			if fp:
				return fp
		return None
		
	def list_tmpl(self):
		ret = []
		for rp,_ in self.paths:
			p = os.path.abspath(rp)
			[ ret.append(i) for i in listFile(p,suffixs=self.subffixes,rescursive=True) ]	
		return sorted(ret)

