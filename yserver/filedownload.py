import os
import asyncio

import aiofiles
import mimetypes
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web import StreamResponse
from aiohttp import web
from appPublic.rc4 import RC4
from appPublic.registerfunction import RegisterFunction
from appPublic.log import debug
from .filestorage import FileStorage

crypto_aim = 'God bless USA and others'
def path_encode(path):
	rc4 = RC4()
	return rc4.encode(path,crypto_aim)

def path_decode(dpath):
	rc4 = RC4()
	return rc4.decode(dpath,crypto_aim)

async def file_upload(request):
	pass

async def file_download(request, filepath, content_type=None):
	filename = os.path.basename(filepath)
	r = web.FileResponse(filepath)
	ct = content_type
	if ct is None:
		ct, encoding = mimetypes.guess_type(filepath)
	if ct is not None:
		r.content_type = ct
	else:
		r.content_type = 'application/octet-stream'
	r.content_disposition = 'attachment; filename=%s' % filename
	r.enable_compression()
	return r
	if os.path.exists(filepath):
		length = os.path.getsize(filepath)
		response = web.Response(
			status=200,
			headers = {
			'Content-Disposition': 'attrachment;filename={}'.format(filename)
		}
		)
		await response.prepare(request)
		cnt = 0
		async with aiofiles.open(filepath, 'rb') as f:
			chunk = await f.read(10240000)
			cnt = cnt + len(chunk)
			await response.write(chunk)
		await response.fsyn()
		await response.write_eof()
		return response
	raise HTTPNotFound

async def path_download(request, kw, *params):
	path = kw.get('path')
	fs = FileStorage()
	fp = fs.realPath(path)
	debug(f'path_download():download filename={fp}')
	return await file_download(request, fp)

rf = RegisterFunction()
rf.register('download_path', path_download)


	
