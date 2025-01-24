# ahserver

ahserver is a http(s) server base on aiohttp asynchronous framework.

ahserver capabilities:
* user authorization and authentication support
* https support
* processor for registed file type
* pre-defined variables and function can be called by processors
* multiple database connection and connection pool
* a easy way to wrap SQL
* configure data from  json file stored at ./conf/config.json
* upload file auto save under config.filesroot folder
* i18n support
* processors include:
	+ 'dspy' file subffix by '.dspy', is process as a python script
	+ 'tmpl' files subffix by '.tmpl', is process as a template
	+ 'md' files subffix by '.md', is process as a markdown file
	+ 'xlsxds' files subffix by '.xlsxds' is process as a data source from xlsx file
	+ 'sqlds' files subffixed by '.sqlds' is process as a data source from database via a sql command

## python3.12 bug fix
We use aioredis, it use distutils, but above 3.12, distutils not exists, so we need to hack it a bit.

### new model
```
pip install packaging
```
need modify files:
* aioredis/exceptions.py
* aioredis/connection.py
```replace aioredis/connection.py line 11 with
from packaging.version import Version as StrictVersion
```
replace aiotedis/exceptions.py 14 line with:
```
class TimeoutError(asyncio.TimeoutError, RedisError):
```

## Requirements

see requirements.txt

[pyutils](https://github.com/yumoqing/pyutils)

[sqlor](https://github.com/yumoqing/sqlor)

## How to use
see ah.py

```
from ahserver.configuredServer import ConfiguredServer

if __name__ == '__main__':
	server = ConfiguredServer()
	server.run()
```

## Folder structure

+ app
+ |-ah.py
+ |--ahserver
+ |-conf
+      |-config.json
+ |-i18n

## Configuration file content
ahserver using json file format in its configuration, the following is a sample:
```
{
	"databases":{
		"aiocfae":{
			"driver":"aiomysql",
			"async_mode":true,
			"coding":"utf8",
			"dbname":"cfae",
			"kwargs":{
					"user":"test",
					"db":"cfae",
					"password":"test123",
					"host":"localhost"
			}
		},
		"cfae":{
			"driver":"mysql.connector",
			"coding":"utf8",
			"dbname":"cfae",
			"kwargs":{
					"user":"test",
					"db":"cfae",
					"password":"test123",
					"host":"localhost"
			}
		}
	},
	"website":{
		"paths":[
			["$[workdir]$/../usedpkgs/antd","/antd"],
			["$[workdir]$/../wolon",""]
		],
		"host":"0.0.0.0",
		"port":8080,
		"coding":"utf-8",
		"ssl":{
			"crtfile":"$[workdir]$/conf/www.xxx.com.pem",
			"keyfile":"$[workdir]$/conf/www.xxx.com.key"
		},
		"indexes":[
			"index.html",
			"index.tmpl",
			"index.dspy",
			"index.md"
		],
		"visualcoding":{
			"default_root":"/samples/vc/test",
			"userroot":{
				"ymq":"/samples/vc/ymq",
				"root":"/samples/vc/root"
			},
			"jrjpath":"/samples/vc/default"
		},
		"processors":[
			[".xlsxds","xlsxds"],
			[".sqlds","sqlds"],
			[".tmpl.js","tmpl"],
			[".tmpl.css","tmpl"],
			[".html.tmpl","tmpl"],
			[".tmpl","tmpl"],
			[".dspy","dspy"],
			[".md","md"]
		]
	},
	"langMapping":{
		"zh-Hans-CN":"zh-cn",
		"zh-CN":"zh-cn",
		"en-us":"en",
		"en-US":"en"
	}
}
```

### database configuration
the ahserver using packages for database engines are:
* oracle:cx_Oracle
* mysql:mysql-connector
* postgresql:psycopg2
* sql server:pymssql

however, you can change it, but must change the "driver" value the the package name in the database connection definition.

in the databases section in config.json, you can define one or more database connection, and also, it support many database engine, just as ORACLE,mysql,postgreSQL.
define a database connnect you need follow the following json format.

* mysql or mariadb
```
                "metadb":{
                        "driver":"mysql.connector",
                        "coding":"utf8",
                        "dbname":"sampledb",
                        "kwargs":{
                                "user":"user1",
                                "db":"sampledb",
                                "password":"user123",
                                "host":"localhost"
                        }
                }
```
the dbname and "db" should the same, which is the database name in mysql database
* Oracle
```
		"db_ora":{
			"driver":"cx_Oracle",
			"coding":"utf8",
			"dbname":sampledb",
			"kwargs":{
				"user":"user1",
				"host":"localhost",
				"dsn":"10.0.185.137:1521/SAMPLEDB"
			}
		}
```

* SQL Server
```
                "db_mssql":{
                        "driver":"pymssql",
                        "coding":"utf8",
                        "dbname":"sampledb",
                        "kwargs":{
                                "user":"user1",
                                "database":"sampledb",
                                "password":"user123",
                                "server":"localhost",
                                "port":1433,
                                "charset":"utf8"
                        }
                }
```
* PostgreSQL
```
		"db_pg":{
			"driver":"psycopg2",
			"dbname":"testdb",
			"coding":"utf8",
			"kwargs":{
				"database":"testdb",
				"user":"postgres",
				"password":"pass123",
				"host":"127.0.0.1",
				"port":"5432"
			}
		}
```
### https support

In config.json file, config.website.ssl need to set(see above)

### website configuration
#### paths
ahserver can serve its contents (static file, dynamic contents render by its processors) resided on difference folders on the server file system.
ahserver finds a content identified by http url in order the of the paths specified by "paths" lists inside "website" definition of config.json file
#### processors
all the prcessors ahserver using, must be listed here.
#### host
by defaualt, '0.0.0.0'
#### port
by default, 8080
#### coding
ahserver recomments using 'utf-8'

### langMapping

the browsers will send 'Accept-Language' are difference even if the same language. so ahserver using a "langMapping" definition to mapping multiple browser lang to same i18n file


## international

ahserver using MiniI18N in appPublic modules in pyutils package to implements i18n support

it will search translate text in ms* txt file in folder named by language name inside i18n folder in workdir folder, workdir is the folder where the ahserver program resided or identified by command line paraments.

## performance

To be list here

## Behind the nginx
when ahserver running behind the nginx, nginx should be forward following header to ahserver

* X-Forwarded-For: client real ip
* X-Forwarded-Scheme: scheme in client browser
* X-Forwarded-Host: host in client browser
* X-Forwarded-Url: url in client browser
* X-Forwarded-Prepath: subfolder name if if ahserver is behind nginx and use subfolder proxy.

## environment for processors

When coding in processors, ahserver provide some environment stuff for build apllication, there are modules, functions, classes and variables

### session environment

* async get_user()
a coroutine to get userid if user not login, it return None
* async remember_user(userid, username='', userorgid='') 
a coroutine to set session user info: userid, name, orgid
* async forget_user()
a coroutine to forget session user information, and get_user() will return None
* async redirect(url)
a coroutine to redirect request to a new url
* entire_url(url)
a function to convert url to a url with http(s)://servername:port/repath/.... format, a outside url will return argument's url without change.
* aiohttp_client
aiohttp_client is aiohttp.client class to make a new request to other server
* gethost()
a function to get client ip
* async path_call(path, **kw)
a coroutine to call other source in server with path
* params_kw
dictionary to storages data tranafers from client. if files upload from client, upload file stored under the folder defined in configure file named by "files", the params_kw only storage the subpath under "files" defined folder.

### global environment


### modules:
* time
* datetime
* random
* json

### functions:
* configValue(k):
function return configuration file value in k, k is start with '.', examples: configValue('.website') will return website value in configuration file; configValue('.website.port') will return port under website in configuration file.

* isNone(v)
a function check v is or not None, if is return True, else return False
* int(v)
a function to convert v to integer
* str(v)
a function to convert v to string
* float(v)
a function to convert v to float
* type(v)
a function to get v's type
* str2date(dstr)
a function to convert string with "YYYY-MM-DD" format to datetime.datetime instance
* str2datetime(dstr)
a function to convert string with "YYYY-MM-DD" format to datetime.datetime instance
* curDatetime()
a function to get current date and time in datetime.datetime instsance
* uuid()
a function to get a uuid value
* DBPools()
a function to get a db connection from sqlor connection pool, further infor see [sqlor](https://git.kaiyuancloud.cn/yumoqing/sqlor)

all the databases it can connected to need to defiend in 'databases' in configuration file.

CRUD use case:

by use CRUD, the table must have a id field as primay key.

CRUD use case 1(insert data to table. in a insert.dspy file)
```
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	ns = {
		'id':uuid(),
		'field1':1
	}
	recs = await sor.C('tbl1', ns)
```

CRUD use case 2(update data in table. in a update.dspy file)
```
ns = params_kw.copy() # get data from client
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	await sor.U('tbl1', ns)
```
CRUD use case 3(delete data in table. in a delete.dspy file)
```
ns = {
	'id':params_kw.id
}
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	await sor.D('tbl1', ns)
```
CRUD use case 4(query date from table, in a search.dspy file)
```
ns = params_kw.copy()
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	recs = await sor.R('tbl1', ns)
	# recs is d list with element is a DictObject instance with all the table fields data
	return recs
```
CRUD use case 5(paging query data from table, in a search_paging.dspy file)
```
ns = params_kw.copy()
if ns.get('page') is None:
	ns['page'] = 1
if ns.get('sort') is None:
	ns['sort'] = 'id desc'
db = DBPools()
async with db.sqlorContext('dbname1') as sor:
	recs = await sor.RP('tbl1', ns)
	# recs is a DictObject instance with two keys: "total": result records, "rows" return data list
	# example:
	# {
	#    "total":423123,
	#    "rows":[ ..... ] max record is "pagerows" in ns, default is 80
	# }
	return recs
```

SQL EXECUTE use case 1
```
sql = "..... where id=${id}$ and field1 = ${var1}$ ..."
db = DBPools()
async with db.sqlorContext('dbname') as sor:
	r = await sor.sqlExe(sql, {'id':'iejkuiew', 'var1':1111})
	# if sql is a select command, r is a list with data returned, is a instance of DictObject
	....
```

SQL EXECUTE use case 2
```
sql = "..... where id=${id}$ and field1 = ${var1}$ ..."
db = DBPools()
async with db.sqlorContext('dbname') as sor:
	r = await sor.sqlPaging(sql, {'id':'iejkuiew', 
								'page':1,
								'pagerows':60,
								'sort':'field1',
								'var1':1111})
	# r is a DictObject instance with two keys: "total": result records, "rows" return data list
	# example:
	# {
	#    "total":423123,
	#    "rows":[ ..... ] max record is "pagerows" in ns, default is 80
	# }
	....
```

### variables
* resource
* terminalType

* ArgsConvert
* curDateString
* curTimeString
* monthfirstday
* strdate_add
* webpath
* stream_response
* rfexe
* basic_auth_headers
* format_exc
* realpath
* save_file
* async_sleep
* DictObject
* 

### classes
* ArgsConvert
