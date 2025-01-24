def unicode_escape(s):
	x = [ch if ord(ch) < 256 else ch.encode('unicode_escape').decode('utf-8') for ch in s]
	return ''.join(x)

