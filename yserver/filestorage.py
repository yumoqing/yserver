# fileUpload.py

import asyncio
import os
import time
import tempfile
import aiofiles
import json
import time

from appPublic.folderUtils import _mkdir
from appPublic.jsonConfig import getConfig
from appPublic.Singleton import SingletonDecorator
from appPublic.log import info, debug, warning, exception, critical

@SingletonDecorator
class TmpFileRecord:
	def __init__(self, timeout=3600):
		self.filetime = {}
		self.changed_flg = False
		self.timeout = timeout
		self.time_period = 10
		self.filename = self.savefilename()
		self.loop = asyncio.get_event_loop()
		self.loop.call_later(0.01, self.load)

	def newtmpfile(self, path:str):
		self.filetime[path] = time.time()
		self.change_flg = True

	def savefilename(self):
		config = getConfig()
		root = config.filesroot or tempfile.gettempdir()
		pid = os.getpid()
		return root + f'/tmpfile_rec_{pid}.json'

	async def save(self):
		if not self.change_flg:
			return
		async with aiofiles.open(self.filename, 'bw') as f:
			s = json.dumps(self.filetime)
			b = s.encode('utf-8')
			await f.write(b)
			await f.flush()
			self.change_flg = False

	async def load(self):
		fn = self.filename
		if not os.path.isfile(fn):
			return
		async with aiofiles.open(fn, 'br') as f:
			b = await f.read()
			s = b.decode('utf-8')
			self.filetime = json.loads(s)

		self.remove()

	def file_useful(self, fpath):
		try:
			del self.filetime[fpath]
		except Exception as e:
			exception(f'Exception:{str(e)}')
			pass

	async def remove(self):
		tim = time.time()
		ft = {k:v for k,v in self.filetime.items()}
		for k,v in ft:
			if tim - v > self.timeout:
				self.rmfile(k)
				del self.tiletime[k]
		await self.save()
		self.loop.call_later(self.time_period, self.remove)

	def rmfile(self, name:str):
		config = getConfig()
		os.remove(config.fileroot + name)
	
class FileStorage:
	def __init__(self):
		config = getConfig()
		self.root = os.path.abspath(config.filesroot or tempfile.gettempdir())
		self.tfr = TmpFileRecord()
	
	def realPath(self,path):
		if path[0] == '/':
			path = path[1:]
		p = os.path.abspath(os.path.join(self.root,path))
		return p

	def webpath(self, path):
		if path.startswith(self.root):
			return path[len(self.root):]

	def _name2path(self,name, userid=None):
		name = os.path.basename(name)
		paths=[191,193,197,97]
		v = int(time.time()*1000000)
		# b = name.encode('utf8') if not isinstance(name,bytes) else name
		# v = int.from_bytes(b,byteorder='big',signed=False)
		root = self.root
		if userid:
			root += f'/{userid}'
		path = os.path.abspath(os.path.join(root,
					str(v % paths[0]),
					str(v % paths[1]),
					str(v % paths[2]),
					str(v % paths[3]),
					name))
		return path

	def remove(self, path):
		try:
			if path[0] == '/':
				path = path[1:]
			p = os.path.join(self.root, path)
			os.remove(p)
		except Exception as e:
			exception(f'{path=}, {p=} remove error')
			
	async def save(self,name,read_data, userid=None):
		p = self._name2path(name, userid=userid)
		fpath = p[len(self.root):]
		info(f'{p=}, {fpath=},{self.root} ')
		_mkdir(os.path.dirname(p))
		if isinstance(read_data, str) or isinstance(read_data, bytes):
			b = read_data
			if isinstance(read_data, str):
				b = read_data.encode('utf-8')
			async with aiofiles.open(p, 'wb') as f:
				await f.write(b)
				await f.flush()
			self.tfr.newtmpfile(fpath)		
			return fpath

		async with aiofiles.open(p,'wb') as f:
			siz = 0
			while 1:
				d = await read_data()
				if not d:
					break
				siz += len(d);
				await f.write(d)
				await f.flush()
		self.tfr.newtmpfile(fpath)		
		return fpath

def file_realpath(path):
	fs = FileStorage()
	return fs.realPath(path)

