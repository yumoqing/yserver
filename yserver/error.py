def Error(errno='undefined error',msg='Error'):
	return {
		"status":"Error",
		"data":{
			"message":msg,
			"errno":errno
		}
	}

def Success(data):
	return {
		"status":"OK",
		"data":data
	}

def NeedLogin(path):
	return {
		"status":"need_login",
		"data":path
	}

def NoPermission(path):
	return {
		"status":"no_permission",
		"data":path
	}

