# yserver

yserver is a branch from [aherver](https://github.com/yumoqing/ahserver), between the yserver and web server it based on, there is a new isolating layer exists, we call it Webserver API(WAPI).

WAPI incloudes web server api, authentication api, request object api and respnse object operation api

Yserver will implements WAPI for most populur python web server, so yserver can base on any of the web server which has WAPI.

## yserver feature

* user authentication and authorization
* simple database op
* websocket
* register function request handler
* predefined documents type handler(template, distictly python script, fontend ui template, etc.)

## roadmap

* WAPI definition.
* WAPI for aiohttp
* WAPI or robyn(fastest web server).

