import uuid
import random

# Script to generate 500 HTML pages with random data
# HTML files will be placed in /vagrant/web/html/random/ directory
# With vagrant web, can be accessed via 10.10.10.10/random

def main():
    for i in range(1,501):
        filename = r'/vagrant/web/html/random/' +str(i) + '.html'
        genPage(filename, i)

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
    main()
