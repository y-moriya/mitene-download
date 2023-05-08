#!/usr/bin/env python
# coding: utf-8

import sys

from mitene_scraper import MiteneScraper

if __name__ == '__main__':
    with MiteneScraper() as scraper:
        is_download_all = (len(sys.argv) == 2 and sys.argv[1] == '--all')
        if (is_download_all):
            scraper.run_newsfeed_all()
        else:
            scraper.run_newsfeed()
    sys.exit(0)
