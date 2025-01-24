import os, sys
import argparse
from appPublic.log import MyLogger, info, debug, warning
from appPublic.folderUtils import ProgramPath
from appPublic.jsonConfig import getConfig
from ahserver.configuredServer import ConfiguredServer
from ahserver.serverenv import ServerEnv
from appPublic.jsonConfig import getConfig
		
def webapp(init_func):
	parser = argparse.ArgumentParser(prog="Sage")
	parser.add_argument('-w', '--workdir')
	parser.add_argument('-p', '--port')
	args = parser.parse_args()
	workdir = args.workdir or os.getcwd()
	p = ProgramPath()
	config = getConfig(workdir, NS={'workdir':workdir, 'ProgramPath':p})
	if config.logger:
		logger = MyLogger(config.logger.name or 'webapp',
							levelname=config.logger.levelname or 'info',
							logfile=config.logger.logfile or None)
	else:
		logger = MyLogger('webapp', levelname='info')
	init_func()
	server = ConfiguredServer(workdir=workdir)
	port = args.port or config.website.port or 8080
	port = int(port)
	server.run(port=port)

if __name__ == '__main__':
	from main import main
	webapp(main)
