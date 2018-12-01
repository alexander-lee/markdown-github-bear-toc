# encoding=utf-8
# python3.6

import sqlite3
import os
from os import path
import re
import argparse
from urllib.parse import quote
import datetime as dt
from dateutil.relativedelta import relativedelta

HOME = os.getenv('HOME', '')

bear_db = path.join(HOME, 'Library/Group Containers/9K33E3U3T4.net.shinyfrog.bear/Application Data/database.sqlite')

parser = argparse.ArgumentParser(description='Markdown Table of Contents Generator for Bear or Github', add_help=False)

parser.add_argument('--help', action='help',
                    help='Show this help message and exit')

parser.add_argument('name', nargs='+', type=str,
                    help='Bear Note UUID, Bear Note Title, Bear Note Tag, or Markdown file')

parser.add_argument('-h', '--header-priority', type=int, dest='header_priority', default=3,
                    help='(Default: 3) Maximum Header Priority/Strength to consider as Table of Contents')

parser.add_argument('-t', '--type', type=str.lower, dest='type', choices=['github', 'bear'], default='github',
                    help='(Default: github) Github Anchors or Bear Anchors')

parser.add_argument('--no-write', dest='write', action='store_false',
                    help='(Default: True) Whether or not write Table of Contents to file or note automatically')

parser.add_argument('-toc', '--table-of-contents-style', dest='toc', default='# Table of Contents',
                    help='(Default: \'# Table of Contents\') Table of Contents Style')

parser.set_defaults(write=True)

args = parser.parse_args()
params = vars(args)

if (params['type'] == 'bear'):
    conn = sqlite3.connect(bear_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()


def get_notes_from_bear():
    """
    Returns all Bear Notes specified which have specified title or UUID.
    """
    # Get all Unarchived notes from Bear
    read_query = "SELECT * FROM `ZSFNOTE` WHERE `ZTRASHED` LIKE '0' AND `ZARCHIVED` LIKE '0'"
    notes = cursor.execute(read_query)

    def match_title_uuid_tag(note):
        note_tags = get_tags_in_note(note['ZTEXT'])
        for query in params['name']:
            if query in note_tags or query == note['ZTITLE'] or query == note['ZUNIQUEIDENTIFIER']:
                return True
        return False

    return list(filter(lambda note: match_title_uuid_tag(note), notes))


def get_tags_in_note(md_text):
    """
    Returns a set of tags that exist in the note using the RegEx. Tags are elements that are preceeded by '#'.
    """

    # First, ignore all code blocks since our regex is unable to handle it
    text_no_code = []

    lines_iter = iter(md_text.splitlines())
    in_code_block = False
    for line in lines_iter:
        if line.startswith('```'):
            in_code_block = not in_code_block

        if not in_code_block:
            text_no_code.append(line)

    text_no_code = '\n'.join(text_no_code)

    # Match all tags
    # Positive Lookbehind 1: Start of character
    # Positive Lookbehind 2: newline character or ' ' (needs to be separate cause Python only takes fixed-length lookbehinds)
    # Group 1: Starts with '#' and ends with '#' as long as middle is not '#' or a newline character (#tags#)
    # Group 2: Starts with '#' and is not succeeded by a '#', ' ', or newline character (#tags)
    # We need two groups because '#tags#' can have spaces where '#tags' cannot
    tag_matches = re.findall(r'((?<=^)|(?<=\n|\r| ))(#[^#\r\n]+#|#[^#\r\n ]+)', text_no_code, re.MULTILINE)
    tag_matches = map(lambda match: match[1], tag_matches)  # Second Capture Group
    return set(tag_matches)


def has_table_of_contents(md_text):
    """
    Return True or False whether or not a Table of Contents header already exists in the given Markdown text.
    """
    return re.search(r'^#+\sTable\sof\sContents', md_text, re.IGNORECASE | re.MULTILINE) is not None


def get_headers(md_text, max_priority):
    """
    Retrieves a list of header, priority pairs in a given Markdown text.

    Format: (Header Title, Priority)
    """
    lines_iter = iter(md_text.splitlines())

    # Skip the first line because it's the Title
    next(lines_iter)

    # List of Tuples: (Header Title, Number of #)
    header_priority_pairs = []
    in_code_block = False
    for line in lines_iter:
        if line.startswith('```'):
            in_code_block = not in_code_block

        elif not in_code_block and line.startswith('#') and ' ' in line:
            md_header, header_title = line.split(' ', 1)

            # Check if md_header has all '#'
            if md_header != md_header[0] * len(md_header):
                continue

            # Check if md_header is of lower priority than listed
            if len(md_header) > max_priority:
                continue

            if header_title.lower() != 'table of contents' and len(header_title) > 1:
                header_priority_pairs.append((header_title, len(md_header)))

    return sequentialize_header_priorities(header_priority_pairs)


def sequentialize_header_priorities(header_priority_pairs):
    """
    In a case where a H3 or H4 succeeds a H1, due to the nature of the Table of Contents generator\
    which adds the number of tabs corresponding to the header priority/strength, this will sequentialize\
    the headers such that all headers have a priority of atmost 1 more than their preceeding header.

    [('Header 1', 1), ('Header 3', 3), ('Header 4', 4)] -> [('Header 1', 1), ('Header 2', 2), ('Header 3', 3)]
    """
    # Go through each header and and if we see a pair where the difference in priority is > 1, make them sequential
    # Ex: (H1, H3) -> (H1, H2)
    for i in range(len(header_priority_pairs) - 1):
        header, priority = header_priority_pairs[i]
        next_header, next_priority = header_priority_pairs[i + 1]

        if (next_priority - priority > 1):
            header_priority_pairs[i + 1] = (next_header, priority + 1)

    return header_priority_pairs


def create_bear_header_anchor(header_title, note_uuid):
    """
    Returns a markdown anchor of a Bear x-callback-url to the header.
    """
    header_title_url_safe = quote(header_title)
    return '[{}](bear://x-callback-url/open-note?id={}&header={})'.format(header_title, note_uuid, header_title_url_safe)


def create_github_header_anchor(header_title):
    """
    Returns a Github Markdown anchor to the header.
    """
    return '[{}](#{})'.format(header_title, header_title.replace(' ', '-'))


def create_table_of_contents(header_priority_pairs, note_uuid=None):
    """
    Returns a list of strings containing the Table of Contents.
    """
    if len(header_priority_pairs) == 0:
        return None

    bullet_list = [params['toc']]

    highest_priority = min(header_priority_pairs, key=lambda pair: pair[1])[1]
    for header, priority in header_priority_pairs:
        md_anchor = create_bear_header_anchor(header, note_uuid) if params['type'] == 'bear' else create_github_header_anchor(header)
        bullet_list.append('\t' * (priority - highest_priority) + '* ' + md_anchor)

    # Specifically for Bear add separator
    if params['type'] == 'bear':
        bullet_list.append('---')

    return bullet_list


def create_table_of_contents_bear():
    """
    Read Bear Notes and returns list of (Original Text, Table of Contents List) and list of note UUIDs.
    """
    notes = get_notes_from_bear()
    md_text_toc_pairs = []
    uuids = []

    for row in notes:
        title = row['ZTITLE']
        md_text = row['ZTEXT'].rstrip()
        uuid = row['ZUNIQUEIDENTIFIER']
        # creation_date = row['ZCREATIONDATE']
        # modified = row['ZMODIFICATIONDATE']

        if has_table_of_contents(md_text):
            print('[WARNING]: \'{}\' already has a Table of Contents, Ignoring...'.format(title))
            continue

        header_list = get_headers(md_text, params['header_priority'])
        table_of_contents_lines = create_table_of_contents(header_list, uuid)

        if table_of_contents_lines is None:
            print('[WARNING]: \'{}\' has no headers to create a Table of Contents, Ignoring...'.format(title))
            continue

        if (params['write']):
            print('Creating a Table of Contents for \'{}\''.format(title))

        md_text_toc_pairs.append((md_text, table_of_contents_lines))
        uuids.append(uuid)

    return md_text_toc_pairs, uuids


def create_table_of_contents_github():
    """
    Read from file and returns list of (Original Text, Table of Contents List).
    """
    md_text_toc_pairs = []
    valid_filepaths = []

    for filepath in params['name']:
        name, ext = path.splitext(filepath)

        if ext.lower() != '.md':
            print('[WARNING]: {} is not a Markdown File, Ignoring...'.format(filepath))
            continue

        try:
            with open(filepath, 'r') as file:
                md_text = file.read()

                if has_table_of_contents(md_text):
                    print('[WARNING]: {} already has a Table of Contents, Ignoring...'.format(filepath))
                    continue

                header_list = get_headers(md_text, params['header_priority'])
                table_of_contents_lines = create_table_of_contents(header_list)

                if table_of_contents_lines is None:
                    print('[WARNING]: {} has no headers to create a Table of Contents, Ignoring...'.format(filepath))
                    continue

                if (params['write']):
                    print('Creating a Table of Contents for \'{}\''.format(filepath))

                md_text_toc_pairs.append((md_text, table_of_contents_lines))
                valid_filepaths.append(filepath)

        except OSError:
            print('[ERROR]: {} doesn\'t exist or cannot be read, Ignoring...'.format(filepath))

    return md_text_toc_pairs, valid_filepaths


def find_note_contents_start(md_text_lines):
    """
    Some notes in Bear contain #tags near the title. This returns the index in the list that\
    isn't the title or contains tags. If no index found, return len(md_text_lines)
    """
    # Start at 1 to skip the title
    # Look for regex matches of tags and if lines from the top contain tags, then skip
    for i in range(1, len(md_text_lines)):
        if re.search(r'((?<=^)|(?<=\n|\r| ))(#[^#\r\n]+#|#[^#\r\n ]+)', md_text_lines[i]) is None:
            return i

    return len(md_text_lines)


def convert_bear_timestamp(datetime=dt.datetime.now()):
    """For some weird reason Bear's timestamps are 31 years behind, so this returns 'datetime' - 31 years as a Unix Timestamp."""
    return (datetime - relativedelta(years=31)).timestamp()


def main():
    md_text_toc_pairs = None
    identifiers = None  # Either Bear Note UUIDs or File Paths

    if (params['type'] == 'bear'):
        md_text_toc_pairs, identifiers = create_table_of_contents_bear()
    elif (params['type'] == 'github'):
        md_text_toc_pairs, identifiers = create_table_of_contents_github()

    for i, (md_text, toc_lines) in enumerate(md_text_toc_pairs):
        if (params['write']):
            # Inject Table of Contents (Title, \n, Table of Contents, \n, Content)
            text_list = md_text.splitlines()
            content_start = find_note_contents_start(text_list)

            updated_text_list = [*text_list[:content_start], '', *toc_lines, '', *text_list[content_start:]]
            # Regex extracts anchor text from ancho
            # NOTE: There are edge cases with code blocks, bold, strikethroughs, etc...
            subtitle_text = re.sub(r'\[([^\[\]]+)\]\([^\(\)]+\)', r'\1', ' '.join(updated_text_list[1:]))
            updated_md_text = '\n'.join(updated_text_list)

            if (params['type'] == 'bear'):
                # Update Note with Table of Contents
                update_query = "UPDATE `ZSFNOTE` SET `ZSUBTITLE`=?, `ZTEXT`=?, `ZMODIFICATIONDATE`=? WHERE `ZUNIQUEIDENTIFIER`=?"
                cursor.execute(update_query, (subtitle_text, updated_md_text, convert_bear_timestamp(), identifiers[i]))
                conn.commit()
            elif (params['type'] == 'github'):
                # Update File
                with open(identifiers[i], 'w') as file:
                    file.write(updated_md_text)

        else:
            print('\n'.join(toc_lines) + '\n')


if __name__ == '__main__':
    main()

    if params['type'] == 'bear' and params['write']:
        print('==================== [DONE] ====================')
        print('[WARNING]: There still might be syncing issues with iCloud, for a precautionary measure, edit the note again.')
        print('To see your changes, please restart Bear!')

    if params['type'] == 'bear':
        conn.close()


# DEPRECATED
# def create_header_list(header_priority_pairs):
#     # Base Case
#     if (len(header_priority_pairs) == 0):
#         return []
#
#     header_list = []
#     current_header = None
#     current_priority = None
#     current_subheaders = []
#
#     # Go through each header and check if the header's priority is greater than the next's
#     for i in range(len(header_priority_pairs) - 1):
#         header, priority = header_priority_pairs[i]
#         next_header, next_priority = header_priority_pairs[i + 1]
#
#         if current_header is None:
#             current_header = header
#             current_priority = priority
#
#         # Append Sub-header
#         current_subheaders.append(header_priority_pairs[i + 1])
#
#         # If we see a same ranked header (H1 and H1) or reaches the end
#         if current_priority == next_priority or i + 1 == len(header_priority_pairs) - 1:
#             header_list.append((current_header, create_header_list(current_subheaders)))
#
#             # Reset Current Header
#             current_header = None
#             current_priority = None
#             current_subheaders = []
#
#     return header_list
