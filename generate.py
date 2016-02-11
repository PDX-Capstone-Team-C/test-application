import uuid
import random
import sys
import os
import errno

# Script to generate N HTML pages with random data
#	Usage: python generate N directory
# HTML files will be placed in /vagrant/web/html/random/[directory]
# With vagrant web, can be accessed via 10.10.10.10/random

def main(argv):
		N = int(sys.argv[1])
		for i in range(1, N):
				directory = r'/vagrant/web/html/random/' + sys.argv[2]
				checkDir(directory)
				filename = str(i) + '.html'
				genPage(directory + '/' + filename, i)
		genPage(directory + '/' + 'index.html', N)
		

def checkDir(directory):
		try:
			os.makedirs(directory)
		except OSError as exception:
			if exception.errno != errno.EEXIST:
				raise
				
def genPage(filename, i):
    file = open(filename, 'w')
    file.write('<!DOCTYPE html>')
    file.write('<html>\n')
    file.write('<body>\n')
    if i > 1:
        tag = '<a href="{0}.html">{0}</a>'.format(i - 1)
        file.write(tag  + '\n')
    genContent(file)
    file.write('</body>\n')
    file.write('</html>\n')
    file.close()

def genContent(file):
    random.seed()
    for i in range (1, random.randint(3, 15)):
        file.write('<p>\n')
        for j in range (1, random.randint(20, 100)):
            x = uuid.uuid4()
            file.write(str(x) + '<br>\n')
        file.write('</p>\n')

if __name__ == '__main__':
    main(sys.argv[1:])
