#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2018 Jan Holthuis
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import argparse
import logging
import os
import re
import sqlite3
import bs4

DBPATH = 'Contents/Resources/docSet.dsidx'
DOCPATH = 'Contents/Resources/Documents'
DOCSET = 'Intel_x86_IA32'
DOCSET_DIR = '%s.docset' % DOCSET
INSTR_PATTERN = re.compile(r'^(?:\./)?(?P<filename>[\w:-]+\.html)$')


def parse_index(fp):
    logger = logging.getLogger(__name__)
    soup = bs4.BeautifulSoup(fp, 'html.parser')
    for i, tag in enumerate(soup.find_all('a', {'href': INSTR_PATTERN})):
        name = tag.text.strip()
        if not name:
            continue

        matchobj = INSTR_PATTERN.match(tag.attrs['href'])
        if not matchobj:
            continue

        path = matchobj.group('filename')
        if path == 'index.html':
            continue

        logger.info('Found "%s" (path: %s)', name, path)
        yield (name, 'instruction', path)


def update_db(dbpath, data, commit=True):
    logger = logging.getLogger(__name__)
    logger.info('Connecting to database at: %s', dbpath)
    conn = sqlite3.connect(dbpath)
    cur = conn.cursor()

    try:
        cur.execute('DROP TABLE IF EXISTS searchIndex;')
        cur.execute('CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, '
                    'name TEXT, type TEXT, path TEXT);')
        cur.execute('CREATE UNIQUE INDEX anchor ON searchIndex (name, type, '
                    'path);')
        cur.executemany('INSERT OR IGNORE INTO searchIndex(name, type, path) '
                        'VALUES (?,?,?)', list(data))
    except sqlite3.Error:
        logger.error('An error ocurred, rolling back database changes...',
                     exc_info=logger.isEnabledFor(logging.DEBUG))
        conn.rollback()
    else:
        if commit:
            logger.info('Committing database changes...')
            conn.commit()
        else:
            logger.warning('Committing has been disabled, rolling back '
                           'database changes...')
            conn.rollback()
    finally:
        cur.close()
    logger.info('Done.')


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--root', default='.',
                        help='root path of the docset')
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='do not write changes to the database')
    p_args = parser.parse_args(args)

    docset_root = os.path.join(p_args.root, DOCSET_DIR)
    dbpath = os.path.join(docset_root, DBPATH)
    indexpath = os.path.join(docset_root, DOCPATH, 'index.html')

    logging.basicConfig(level=logging.INFO)
    with open(indexpath, mode='r') as f:
        update_db(dbpath, parse_index(f), commit=not p_args.dry_run)


if __name__ == '__main__':
    main()