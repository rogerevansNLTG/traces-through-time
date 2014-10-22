#!/usr/bin/env python

"""
Squash marked up TTT Early Modern data from tabular format to
simple text format with each row treated as a paragraph, and
each cell treated as line. We drop the distinction between
whitespace within the cells and linebreaks, so don't read any
clever semantics into the whitespace.
"""


from __future__ import print_function
from os import path as fp
import argparse
import codecs
import glob
import htmlentitydefs
import math
import os
import re
import xml.etree.ElementTree as ET

from ttt.date import read_date

_OTHER_ENTITIES = {'emacr': 275,
                   'utilde': 361}


# lifted from http://effbot.org/zone/re-sub.htm#unescape-html
# and lightly linted
# exceptions for xml entities added and support for a dictionary
# of additional entities to try
def unescape(text, extra=None):
    """
    Removes HTML character references and entities from a text string.

    :param text The HTML (or XML) source text.
    :return The plain text, as a Unicode string, if necessary.
    """
    _xml_predefined = ["quot", "amp", "apos", "lt", "gt"]
    extra = extra or _OTHER_ENTITIES

    def fixup(match):
        "given a matching entity, return corresponding unicode char"
        text = match.group(0)
        ename = text[1:-1]
        if ename in _xml_predefined:
            return text
        elif text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        elif ename in extra:
            return unichr(extra[ename])
        elif ename in htmlentitydefs.name2codepoint:
            return unichr(htmlentitydefs.name2codepoint[ename])
        return text  # leave as is
    return re.sub(r"&#?\w+;", fixup, text)

# ---------------------------------------------------------------------
#
# ---------------------------------------------------------------------


def _column_to_text(xml):
    """
    string representation of table column - join all text and ignore
    the markup; will have to watch out for unwanted concatenation if
    there are annotations that assume markup implies whitespace
    """
    return "".join(xml.itertext())


def _convert_row(doc_date, xml):
    """
    Given a default date (for the whole document) and a (date, entry)
    row, return

    * a (partial) iso string for the date
    * the text for the entry
    """
    ths = list(xml.iter('th'))
    tds = list(xml.iter('td'))
    if len(ths) < 1 or len(tds) < 1:
        return None
    elif len(ths) > 1:
        ET.dump(xml)
        raise Exception("Did not expect more than one th node")
    elif len(tds) > 1:
        ET.dump(xml)
        raise Exception("Did not expect more than one td node")

    columns = ths + tds
    th_text = ths[0].text or ""
    # This is surely a (one time) typo for Feb 20, but I'm not chancing
    # it. In any case, it (rightly) confuses the date parser
    if th_text and th_text.startswith("Feb. 30"):
        th_text = "Feb"
    date = read_date(th_text, prefix=doc_date, fuzzy=True) # or doc_date
    text = "\n".join(map(_column_to_text, columns))
    return date, text


def _convert_doc(doc_date, xml):
    """
    string representation of entire document
    (WARNING: mutates the tree)
    """
    for br_node in xml.iter('br'):
        br_node.text = "\n"
    return [_convert_row(doc_date, r) for r in xml.iter('tr')]


def convert(ifile):
    """
    Return a list of date, string tuples for each row in the table
    """
    # The data is actually iso-8859-1 converted but it
    # contains entities which are defined elsewhere,
    # so without access to the DTD, we manually translate
    # the entities to unicode chars, encode everything
    # as 'utf-8' and then feed it to a forced-utf-8
    # XML parser
    #
    # Is there a cleaner way to do this?
    parser = ET.XMLParser(encoding='utf-8')
    with codecs.open(ifile, 'r', 'iso-8859-1') as fin:
        utext = unescape(fin.read()).encode('utf-8')
        tree = ET.fromstringlist([utext], parser=parser)
        date_nodes = [n.text for n in tree.iter('head')]
        date_str = read_date(date_nodes[0]) if date_nodes else 'unknown'
        return _convert_doc(date_str, tree)


def _do_file(text_dir, ifile):
    """
    Write converted output for a given file
    """
    rows = convert(ifile)
    if not rows:
        return
    zwidth = int(math.floor(math.log10(len(rows)))) + 1
    for i, row in enumerate(x for x in rows if x):
        bname = fp.basename(ifile)
        tbase = "{prefix}-{row}".format(prefix=fp.splitext(bname)[0],
                                        row=str(i).zfill(zwidth))
        tfile = fp.join(text_dir, tbase)
        with codecs.open(tfile, 'w', 'utf-8') as fout:
            print("\n\n".join(x for x in row if x), file=fout)


def main():
    """
    Read input dir, dump in output dir
    """
    psr = argparse.ArgumentParser(description='TTT converter')
    psr.add_argument('input', metavar='DIR', help='dir with xml files')
    psr.add_argument('output', metavar='DIR', help='output directory')
    args = psr.parse_args()
    text_dir = fp.join(args.output)
    if not fp.exists(text_dir):
        os.makedirs(text_dir)
    for ifile in glob.glob(fp.join(args.input, '*.xml')):
        _do_file(text_dir, ifile)


main()
