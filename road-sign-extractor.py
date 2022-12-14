#!/usr/bin/env python3

from html import escape
from html.parser import HTMLParser
from urllib.request import urlopen

url = "https://likumi.lv"
csn = url + "/ta/id/274865"
signs = []

class Parser(HTMLParser):
    def __init__(self):
        self.started = False
        self.ended = False
        self.data_expected = False
        self.first_column = True
        super().__init__()

    def handle_starttag(self, tag, attrs):
        if self.started and not self.ended:
            if tag == "td":
                if self.first_column:
                    self.data_expected = True
                    self.first_column = False
            elif tag == "img":
                signs[-1][-1].append(attrs)

    def handle_endtag(self, tag):
        if self.started and not self.ended:
            if tag == "td":
                self.data_expected = False
            elif tag == "tr":
                self.first_column = True

    def handle_data(self, data):
        if not self.started:
            if data == "Ceļa zīmes":
                self.started = True
        elif not self.ended:
            if data == "Ceļa apzīmējumi":
                self.ended = True
            elif self.data_expected:
                signs.append((data, []))

Parser().feed(urlopen(csn).read().decode())

for number, images in signs:
    if len(images) > 0:
        with open(f"{number}.html", "w") as html:
            for image in images:
                html.write("<img")

                for attribute, value in image:
                    html.write(" ")
                    html.write(attribute)
                    html.write("=")

                    if attribute == "src":
                        value = url + value

                    html.write(f"\"{escape(value)}\"")

                html.write("/>\n")
