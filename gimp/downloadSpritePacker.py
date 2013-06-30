import urllib2
url ='http://registry.gimp.org/files/Sprite%20Sheet%20Packer.zip'
req = urllib2.urlopen(url)
CHUNK = 16 * 1024
file = 'spriteSheetPacker.zip'
with open(file, 'wb') as fp:
  while True:
    chunk = req.read(CHUNK)
    if not chunk: break
    fp.write(chunk)
