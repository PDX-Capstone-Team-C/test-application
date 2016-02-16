from __future__ import division
import scrapy
from twisted.internet import reactor, defer
from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner
from scrapy.crawler import Crawler
from scrapy.utils.log import configure_logging
from scrapy.spiders import CrawlSpider, Rule
from scrapy.selector import HtmlXPathSelector
from scrapy.linkextractors import LinkExtractor
import filecmp
import os
from os.path import join, getsize
import sys
from commands import getstatusoutput

# A handy enum for the tests tuple used below
SPIDER = 0
SETTING = 1

# Default cache directory
# Change this to set the directory that the cache files will be output to
# each spider will place its cache in a subdirectory of this location
# with spidername_default and spidername_delta
HTTPCACHE_DIR = '/home/vagrant/scrapy-cache/'

# List of cache storages(Backends) that need to be compared
# Format: [key, backend] where:
#       key = alias name, handy shorthand for long backend
#       backend = Actual class in a scrapy/scrapy/extensions/httpcache.py file
BACKENDS = {
    'DEFAULT': 'scrapy.extensions.httpcache.FilesystemCacheStorage',
    'DELTA': 'scrapy.extensions.httpcache.DeltaLeveldbCacheStorage',
    'LEVLEDB': 'scrapy.extensions.httpcache.LeveldbCacheStorage'
}


#============================== DATA STRUCTURES =============================
# String names for the spider classes. NOTE: WE use eval() to call a class.
spiders = [
    "FanficSpider",
    "XkcdSpider",
]

# The list of spiders tests to run. Each item is 2-tuple with the first item
# being the spider to run and the second being the settings object with
# which to run it
spider_tests = []

# A dictionary storing the results of a test run in the following format:
# 'name'    : [str] spider name
# 'backend' : [str] backend key,
# 'correct' : [bool] True/False  true if the html files are the same,
# 'dir_size': [int] the size of the cache directory
# 'weissman': [int] weissman compression score
results = []
#============================= END DATA STRUCTURES ============================


#============================= UTILITY FUNCTIONS ==============================
def get_new_settings(directory, backend):
    """
    A utility function to set a series of Settings parameters to avoid some
    code reduplication/boiler plate lameness. It always sets the Settings
    object's HTTPCACHE_ENABLED to True. This is done in "functional style"
    (rather than mutate a passed in Settings object, we just pass back a newly
    created one)
    :param directory: Directory to output cache to
    :param backend: Cache backend to use
    :return: Settings
    """
    s = Settings()
    s.set('HTTPCACHE_ENABLED', True)
    s.set('HTTPCACHE_DIR', HTTPCACHE_DIR + directory)
    s.set('HTTPCACHE_STORAGE', backend)
    s.set('COMPRESSION_ENABLED', False)
    return s

def generate_test_results(test_list=spider_tests, backends=BACKENDS):
    """
    Generates the results needed to display for each spider test.

    :param test_list: [list] of dictionaries of all spider tests that have
    ran by now.
    :param backends: [list] of dictionaries of all backends for which the
    tests ran.
    :return: [list] of dictionaries per each spider test in format:
        spider_name: [str]
        backend: [str] key value for backend for the test
        correct: [bool] check if the html files are the same
        dir_size: [int] the size of the cache directory
        weissman: [int] weissman compression score

        Ex: [{
            'weissman': 0,
            'correct': True,
            'dir_size': 15764,
            'name': 'FanficSpider',
            'backend': 'DEFAULT'
        }]
    """
    test_results = []
    for test in test_list:
        spider = test[SPIDER]
        for backend in backends:
            name = spider.__name__
            test_results.append({
                'name': name,
                'backend': backend,
                'correct': False,
                'dir_size': dir_size(HTTPCACHE_DIR + name + "_" + backend),
                'weissman': 0,
            })

    return test_results

def display_test_results(results, spider_list=spiders, backends=BACKENDS):
    """
    Outputs(Prints) the results of a test to the screen
    :param results: [list] of dictionaries per each spider. Result of
    generate_test_results method.
    :param spider_list: [list] of dictionaries of all spider tests that have
    ran by now and generated results.
    :param backends: [list] of dictionaries of all backends.
    :return:
    """
    # Printing the header line
    header = ""
    for backend in backends:
        header += " \t" + backend
    print "\t" + header

    # Preparing the results in list format
    display_rows = []
    for spider_name in spider_list:
        tests = filter(lambda x: x['name'] == spider_name, results)
        row = {
            0: spider_name,
            1: "  -> Correct: ",
            2: "  -> Dir Size:",
            3: "  -> Weissman:",
            4: "  -> % Diff:  ",
        }

        diff = 100
        first_size = 0
        for backend in backends:
            instance = filter(lambda x: x['backend'] == backend, tests)[0]
            size = instance['dir_size']
            if size > 0 and first_size != 0:
                diff = 100 - ((size / first_size) * 100.00)
            if size > 0 and first_size == 0:
                first_size = size

            row[1] += " \t" + str(instance['correct'])  + "\t"
            row[2] += " \t" + str(instance['dir_size']) + "KB "
            row[3] += " \t" + str(instance['weissman']) + "\t"
            row[4] += " \t" + str("{0:.2f}").format(round(diff,2)) + "% "

        display_rows.append(row)

    # Printing the results (from list format)
    for row in display_rows:
        for elements in row:
            print row[elements]

def dir_size(start_path = HTTPCACHE_DIR):
    """
    Gets the size of a directory. (used for getting the size of a cache dir)
    :param start_path: [str] the directory from which the walk should begin
    :return: [int] the total size of all subdirectories from the start directory
    """
    cmd = "du -s -c -k "+start_path
    code_err, output = getstatusoutput(cmd)
    if code_err == 0:
        return int(output.split()[0])

def write_response_file(self, response, backends=BACKENDS):
    """
    Helper function that writes a response body file. It depends on the
    storage backend to which file it will write.
    :param self: spider self class
    :param response: response returned by spider
    :param backends: [list] of all dictionaries of all backends
    :return:
    """
    for key, backend in backends.items():
        if self.crawler.settings.get('HTTPCACHE_STORAGE') == backend:
            filename = self.__class__.__name__ + '_' + key + '.html'
            with open(filename, 'wb') as f:
                f.write(response.body)
    return

def set_spiders(spider_list=spiders):
    """
    Sets up all the spiders to run all the backends with their
    settings. NOTE: WE use eval() to get class from a string.
    call a class.
    :param spider_list: String names for the spider classes.
    :return: [list] of 2-tuple of (spider, settings) all the cases for the
    tests to run.
    """
    tests = []
    for spider in spider_list:
        a_spider = eval(spider)
        for backend in BACKENDS:
            # Queue a test using the backend
            settings = get_new_settings(a_spider.__name__ + '_' + backend,
                                        BACKENDS[backend])
            tests.append((a_spider, settings))
    return tests

def set_spider(spider, test_list=spider_tests, backends=BACKENDS):
    """
    Prepares a spider to be run by a script. Sets up scrapy settings,
    sets the source and a delta file html files.
    :param spider: [class] A class that is defined for the spider
    :param test_list: [2-tuple] Data structure for tests to be performed
    :return: [2-tuple] of test_list and a comparison_list
    """
    for backend in backends:
        # Queue a test using the backend
        test_list.append((spider, get_new_settings(spider.__name__ + '_' +
                                                   backend, BACKENDS[backend])))
    return test_list
#============================= END UTILITY FUNCTIONS ==========================


#============================= SPIDERS ========================================
class FanficSpider(scrapy.spiders.CrawlSpider):
    """
    A Fanfic Spider to grab some data that (hopefully) is a bad candidate
    for delta compression. Work in progress.
    """
    name = "fanfic_test"
    allowed_domains = ["www.fanfiction.net"]
    start_urls = ["https://www.fanfiction.net/comic/Scott-Pilgrim/"]
    custom_settings = {
        "DEPTH_LIMIT": 1
    }

    rules = ( Rule(LinkExtractor(allow=()),callback="handle_page", follow=True),)

    def handle_page(self, response):
        # if self.crawler.settings.get('HTTPCACHE_STORAGE') == DEFAULT:
        #     filename = 'FanficSpider_default.html'
        # else:
        #     filename = 'FanficSpider_delta.html'
        # with open(filename, 'wb') as f:
        #     f.write(response.body)
        return response

class XkcdSpider(scrapy.Spider):
    """
    Another spider that scrapes the web VM
    """
    name = "xkcd"
    allowed_domains = ["10.10.10.10"]
    start_urls = (
        'http://10.10.10.10/',
    )

    def parse(self, response):
        write_response_file(self, response)

        # Safe if Xpath is empty, extract handles it.
        prev_link = response.xpath(
                '//*[@id="middleContainer"]/ul[1]/li[2]/a/@href').extract()
        if prev_link:
            url = response.urljoin(prev_link[0])
            yield scrapy.Request(url, callback=self.parse)
#=================================== END SPIDERS ==============================


spider_tests = set_spiders(spiders)

# spider_tests = set_spider(FanficSpider)
# spider_tests = set_spider(XkcdSpider)

# configure_logging()
runner = CrawlerRunner()

@defer.inlineCallbacks
def crawl():
    for spider_test in spider_tests:
        crawler = Crawler(spider_test[SPIDER], spider_test[SETTING])
        yield runner.crawl(crawler)
    reactor.stop()

crawl()
reactor.run()

# Generating results for all tests
results = generate_test_results(spider_tests)

# Now display results and compare
print("==================== SUMMARY ========================")
display_test_results(results)
