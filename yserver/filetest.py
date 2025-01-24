import os

def current_fileno():
	fn = './t.txt'
	f = open(fn, 'w')
	ret = f.fileno()
	f.close()
	os.remove(fn)
	return ret

if __name__ == '__main__':
	for i in range(1000):
		print(current_fileno())

