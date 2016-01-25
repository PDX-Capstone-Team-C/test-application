import scrapy
from twisted.internet import reactor, defer
from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner
from scrapy.crawler import Crawler
from scrapy.utils.log import configure_logging

# A handy enum for the tuple used below
SPIDER = 0
SETTING = 1

# The data structure to hold info for each spider to run
# It consists of a key -- the name of the spider/backend
# and a value -- a tuple consisting of the spider to run
# the settings for the spider and (later) the info to output
# at the end of the test

tests = []

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
        filename = 'fanfic_test.html'
        with open(filename, 'wb') as f:
            f.write(response.body)

# Settings for FanficSpider, one settings object for each backend
# The settings for the first run
settings_def = Settings()
settings_def.set('HTTPCACHE_ENABLED', True)
settings_def.set('HTTPCACHE_DIR', 'fanfic1')
tests.append((FanficSpider, settings_def))

# The settings for the second run
settings_comp = Settings()
# set compression backend here
settings_comp.set('HTTPCACHE_ENABLED', True)
settings_comp.set('HTTPCACHE_DIR', 'fanfic2')
tests.append((FanficSpider, settings_comp))

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
