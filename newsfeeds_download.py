#!/usr/bin/env python
# coding: utf-8

import sys

from mitene_scraper import MiteneScraper

if __name__ == '__main__':
    with MiteneScraper() as scraper:
        scraper.run_newsfeed()
    sys.exit(0)
