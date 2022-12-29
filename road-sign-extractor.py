#!/usr/bin/env python3

from html import escape
from html.parser import HTMLParser
from urllib.request import urlopen

url = "https://likumi.lv"
csn = url + "/ta/id/274865"
doc = [(None, (), [])]

class Parser(HTMLParser):
    # https://www.w3.org/html/wg/spec/syntax.html#void-elements
    void = ("area", "base", "br", "col", "command", "embed", "hr", "img", "input", "keygen", "link", "meta", "param", "source", "track", "wbr")

    def close(self):
        top = doc.pop()
        doc[-1][-1].append(top)

    def handle_starttag(self, tag, attrs):
        assert doc[-1][0] not in self.void, f"void element <{doc[-1][0]}> cannot contain <{tag}>"
        doc.append((tag, attrs, []))

        if tag in self.void:
            self.close()

    def handle_endtag(self, tag):
        if tag not in self.void:
            assert doc[-1][0] == tag, f"<{doc[-1][0]}> element cannot be closed by '{tag}' end tag"
            self.close()

    def handle_data(self, data):
        assert doc[-1][0] not in self.void, f"void element <{doc[-1][0]}> cannot contain {data!r}"
        doc[-1][-1].append(data)

Parser().feed(urlopen(csn).read().decode())
root, = doc

def body(tag, attributes, children):
    if tag == "div" and dict(attributes).get("class") == "doc-body":
        return children

    for child in children:
        if not isinstance(child, str):
            result = body(*child)

            if result is not None:
                return result

def extract(elements):
    interesting = False

    for element in elements:
        if isinstance(element, str):
            assert element.strip() == ""
            continue

        tag, _, children = element
        assert tag == "div"

        if interesting is True:
            yield children
            interesting = False

        strings = [child for child in children if isinstance(child, str)]

        if len(strings) == 1:
            text, = strings

            if text in ("Ceļa zīmes", "Ceļa apzīmējumi"):
                interesting = True

sign_section, marking_section = extract(body(*root))

def table(elements):
    tbody, = elements
    tag, _, rows = tbody
    assert tag == "tbody"
    rowspan = None
    result = []

    for tr in rows:
        def get_text(tag, attributes, children):
            assert tag == "td"
            assert "colspan" not in dict(attributes)
            text, = children
            assert isinstance(text, str), text
            result.append((text, []))
            return int(dict(attributes).get("rowspan", 1))

        def get_image(tag, attributes, children):
            assert tag == "td"
            assert "rowspan" not in dict(attributes)
            assert "colspan" not in dict(attributes)
            img, = children

            if not isinstance(img, str):
                tag, attrs, ch = img

                if tag != "img":
                    assert tag == "p"
                    img, = ch
                    tag, attrs, ch = img

                assert tag == "img"
                assert len(ch) == 0
                result[-1][-1].append(attrs)

        tag, _, cells = tr
        assert tag == "tr"

        if len(cells) == 3:
            assert rowspan is None or rowspan == 0
            number, image, _ = cells
            rowspan = get_text(*number) - 1
            get_image(*image)
        elif len(cells) == 1:
            assert rowspan > 0
            rowspan -= 1
            image, = cells
            get_image(*image)
        else:
            raise

    return result

def signs(elements):
    for element in elements:
        assert not isinstance(element, str)
        tag, _, children = element

        if tag == "p":
            continue

        assert tag == "table"
        for row in table(children):
            yield row

for number, images in signs(sign_section):
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
