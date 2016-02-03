import scrapy
from twisted.internet import reactor, defer
from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner
from scrapy.crawler import Crawler
from scrapy.utils.log import configure_logging
import filecmp
import os
from os.path import join, getsize

# A handy enum for the tests tuple used below
SPIDER = 0
SETTING = 1

# Another handy enum for the comparisons tuple
FILE1 = 0
FILE2 = 1
DIR1 = 2
DIR2 = 3

# Default cache directory
HTTPCACHE_DIR = 'httpcache'

# Handy shorthands for long backend names
DEFAULT = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
DELTA = ''

# DATA STRUCTURES
# The data structure to hold info for each spider to run
# It is a list of tuples where each tuple consists of:
# ( a spider to run, a Settings object to execute the spider with)
tests = []

# The data structure to associate two runs of the same the spider
# with differing backends together, so the test comparisons know what
# things need to be compared against each otherwise
# A list of tuples with each tuple consisting of:
# (the name of the html file generated from default backend,
#  the name of the html file generated from delta backend,
#  the name of the cache directory generated from default backend,
#  the name of the cache directory generated from delta backend)

comparisons = []

# The data structure that will hold the results of doing the comparisons
# for each test. This is the stuff that should be displayed on screen

results = []

# END DATA STRUCTURES

# UTILITY FUNCTIONS

#  A utility function to set a series of Settings parameters to avoid
# some code reduplication/boiler plate lameness. It always sets the Settings
# object's HTTPCACHE_ENABLED to True. This is done in "functional style"
# (rather than mutate a passed in Settings object, we just pass back a newly
# created one)
# Parameters:
# directory: Directory to output cache to
# backend: Cache backend to use
def get_new_settings(directory = HTTPCACHE_DIR,
                     backend = DEFAULT):
    s = Settings()
    s.set('HTTPCACHE_ENABLED', True)
    s.set('HTTPCACHE_DIR', directory)
    s.set('HTTPCACHE_STORAGE', backend)
    s.set('COMPRESSION_ENABLED', False)
    return s

# Takes the resulting files/cache directories after a spider is run
# and generates a few metrics:
# 1 -- compares the two html files generated to see if they are actually correct
# 2 -- compares the sizes of the two cache directories to determine the net
#      difference in space
# Parameters:
# c : s 4-tuple (a comparsion object discussed under data structures)
#     see the enum provided for which item in this tuple corresponds to what
# Returns:
# A dictionary in the following format:
# 'name'       : str         name of the spider
# 'isCorrect'  : True/False  true if the html files are the same,
#                            false otherwise
# 'd1'         : str         the path to the uncompressed directory
# 'd2'         : str         the path to the compressed directory
# 'd1_size'    : num         the size of the uncompressed directory
# 'd2_size'    : num         the size of the compressed directory
# 'size_result': num         the percent size difference

def generate_test_results(c):
    # Compare the fingerprint/checksum of f1/f2 using filecmp
    # Compare the sizes of d1 and d2 using getDirectorySize utility function
    # Return a dictionary in the correct format with the results
    # The imported filecmp package can help with isCorrect
    d1_bytes = getDirectorySize(c[3])
    d2_bytes = getDirectorySize(c[4])
    result = {
        'name' : c[0],
        'isCorrect' : filecmp.cmp(c[1],c[2],True),
        'd1' : c[3],
        'd2' : c[4],
        'd1_size' : d1_bytes,
        'd2_size' : d2_bytes
    }

    if d1_bytes != 0 and d2_bytes != 0 :
        result['size_result'] = ((d2_bytes / d1_bytes) * 100)
    else:
        result['size_result'] = 0

    return result

def display_test_results(r):
    print r['name']
    print "\t%s" % r['isCorrect']
    print "\t%s bytes in %s" % (r['d1_size'], r['d1'])
    print "\t%s bytes in %s" % (r['d2_size'], r['d2'])
    print "\t%.0f%% difference" % r['size_result']
    print "-----"

# Takes the start_path parameter
# adds the sizes of files in current directory,
# and loops through any directories inside of
# the current directory
# Returns number of bytes as int
def getDirectorySize(start_path = HTTPCACHE_DIR):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def setSpider(spiderName):

    # Queue one test using the default backend
    tests.append((spiderName.__name__,
                  get_new_settings(spiderName.__name__ + '_default')))

    # Queue another test using our backend
    tests.append((spiderName.__name__,
                  get_new_settings(spiderName.__name__ + '_delta')))

    # Queue up a test pair result to compare the runs of this spider
    comparisons.append((spiderName.__name__,
                        spiderName.__name__ + '_default.html',
                        spiderName.__name__ + '_delta.html',
                        spiderName.__name__ + '_default',
                        spiderName.__name__ + '_delta'))

# END UTILITY FUNCTIONS

# SPIDERS

# A Fanfic Spider to grab some data that (hopefully) is a bad
# candidate for delta compression. Work in progress.
# Right now this is just being used to test this script
class FanficSpider(scrapy.Spider):
    name = "fanfic_test"
    allowed_domains = ["fanfiction.net"]
    start_urls = [
        "https://www.fanfiction.net/s/11490724/1/Snowflake-s-Passage-First-story-Scary-Things",
        "https://www.fanfiction.net/s/11498367/1/Left-Turn"]

    def parse(self, response):
        if settings.get('HTTPCACHE_STORAGE') == DEFAULT:
            filename = self.__class__.__name__ + '_default.html'
        else:
            filename = self.__class__.__name__ + '_delta.html'
        with open(filename, 'wb') as f:
            f.write(response.body)

# XKCD Spider
class XkcdSpider(scrapy.Spider):
    name = "xkcd"
    allowed_domains = ["10.10.10.10"]
    start_urls = (
        'http://10.10.10.10/',
    )

    def parse(self, response):
        if settings.get('HTTPCACHE_STORAGE') == DEFAULT:
            filename = self.__class__.__name__ + '_default.html'
        else:
            filename = self.__class__.__name__ + '_delta.html'

        with open(filename, 'wb') as f:
            f.write(response.body)

        self.parse_next(self, response)

    def parse_next(self, response):
        # Safe if Xpath is empty, extract handles it.
        prev_link = response.xpath('//*[@id="middleContainer"]/ul[1]/li[2]/a/@href').extract()
        if prev_link:
            url = response.urljoin(prev_link[0])
            yield scrapy.Request(url, callback=self.parseNext)

#END SPIDERS


setSpider(FanficSpider)
setSpider(XkcdSpider)


configure_logging()
runner = CrawlerRunner()

@defer.inlineCallbacks
def crawl():
    for test in tests:
        crawler = Crawler(test[SPIDER], test[SETTING])
        yield runner.crawl(crawler)
    reactor.stop()

crawl()
reactor.run()

# After all spiders have run go ahead and conduct comparisons
results = list(map(generate_test_results, comparisons))

# Now display results of compare
# This should probably be as easy to read as possible
for result in results:
    display_test_results(result)
