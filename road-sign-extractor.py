#!/usr/bin/env python3

from html import escape
from html.parser import HTMLParser
from itertools import chain
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
    return rows

def extract_signs(rows):
    rowspan = None
    result = []

    for tr in rows:
        def get_text(tag, attributes, children):
            assert tag == "td"
            assert "colspan" not in dict(attributes)
            text, = children

            if not isinstance(text, str):
                t, a, c = text
                assert t == "p", t
                assert len(a) == 0
                text, = c
                assert isinstance(text, str)

            return int(dict(attributes).get("rowspan", 1)), text

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
            number, image, name = cells
            rowspan_number, number_text = get_text(*number)
            rowspan_name, name_text = get_text(*name)
            assert rowspan_number == rowspan_name
            rowspan = rowspan_number - 1
            result.append((number_text, name_text, []))
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

        for sign in extract_signs(table(children)):
            yield sign

def markings(elements):
    for element in elements:
        assert not isinstance(element, str)
        tag, _, children = element

        if tag == "p":
            continue

        assert tag == "table"
        numbers = {}
        images = {}
        columns = []

        for row_number, row in enumerate(table(children)):
            column = 0

            def get_content(tag, attributes, children):
                nonlocal column
                assert tag == "td"
                rowspan = int(dict(attributes).get("rowspan", 1))
                assert rowspan != 0
                colspan = int(dict(attributes).get("colspan", 1))
                assert colspan != 0

                while column < len(columns) and columns[column] > 0:
                    columns[column] -= 1
                    column += 1

                content, = children

                if isinstance(content, str):
                    assert rowspan == 1
                    numbers[row_number, column, column + colspan] = content
                else:
                    tag, attributes, _ = content
                    assert tag == "img"
                    images[row_number + rowspan, column, column + colspan] = attributes

                while colspan > 0:
                    if column == len(columns):
                        columns.append(rowspan - 1)
                    else:
                        assert columns[column] == 0
                        columns[column] = rowspan - 1

                    colspan -= 1
                    column += 1

            tag, _, cells = row
            assert tag == "tr"

            for cell in cells:
                get_content(*cell)

            while column < len(columns):
                assert columns[column] > 0, columns[column]
                columns[column] -= 1
                column += 1

        for number_cell, number in numbers.items():
            if number.strip() == "":
                continue

            matching_images = []

            for image_cell, image in images.items():
                if number_cell[0] == image_cell[0] and number_cell[1] <= image_cell[1] and number_cell[2] >= image_cell[2]:
                    matching_images.append(image)

            yield number, None, matching_images

def expand(value):
    return value if value.startswith("http") else url + value

for number, name, images in chain(signs(sign_section), markings(marking_section)):
    if len(images) > 0:
        with open(f"{number}.html", "w") as html:
            html.write("<!DOCTYPE html>\n")
            html.write("<html lang=\"lv\">\n")
            html.write("  <head>\n")
            html.write("    <meta charset=\"UTF-8\" />\n")
            html.write("    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n")
            title = f"{number}." if name is None else f"{number}. {name}"
            html.write(f"    <title>{title}</title>\n")
            html.write(f"    <meta property=\"og:title\" content=\"{escape(title)}\" />\n")
            properties = dict(images[0])
            html.write(f"    <meta property=\"og:image\" content=\"{escape(expand(properties['src']))}\" />\n")

            for property in ("width", "height"):
                if property in properties:
                    html.write(f"    <meta property=\"og:image:{property}\" content=\"{escape(properties[property])}\" />\n")

            html.write("  </head>\n")
            html.write("  <body>\n")
            html.write("    <figure>\n")

            for image in images:
                html.write("      <img")

                for attribute, value in image:
                    html.write(" ")
                    html.write(attribute)
                    html.write("=")

                    if attribute == "src":
                        value = expand(value)

                    html.write(f"\"{escape(value)}\"")

                html.write("/>\n")

            html.write(f"      <figcaption>{title}</figcaption>\n")
            html.write("    </figure>\n")
            html.write("  </body>\n")
            html.write("</html>\n")
