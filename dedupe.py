# encoding=utf8
import sys
import os
import hashlib
import re
import time
import requests


import warcio
from warcio.archiveiterator import ArchiveIterator
from warcio.warcwriter import WARCWriter

if not warcio.__file__ == os.path.join(os.getcwd(), 'warcio', '__init__.pyc'):
    print('Warcio was not imported correctly.')
    print('Location: ' + warcio.__file__ + '.')
    sys.exit(2)

def ia_available(url, digest):
    tries = 0
    print('Deduplicating digest ' + digest + ', url ' + url)
    assert digest.startswith('sha1:')
    digest = digest.split(':', 1)[1]
    hashed = hashlib.sha256(digest + ';' + re.sub('^https?://', '', url)) \
             .hexdigest()
    while tries < 10:
        try:
            tries += 1
            ia_data = requests.get('http://NewsGrabberDedupe.b-cdn.net/{hashed}' \
                                   .format(hashed=hashed), timeout=60)
            if not ';' in ia_data.text:
                return False
            return ia_data.text.split(';', 1)
        except:
            pass
            time.sleep(1)

    return False

def revisit_record(writer, record, ia_record):
    warc_headers = record.rec_headers
    #warc_headers.add_header('WARC-Refers-To'
    warc_headers.replace_header('WARC-Refers-To-Date',
        '-'.join([ia_record[0][:4], ia_record[0][4:6], ia_record[0][6:8]]) + 'T' + 
        ':'.join([ia_record[0][8:10], ia_record[0][10:12], ia_record[0][12:14]]) + 'Z')
    warc_headers.replace_header('WARC-Refers-To-Target-URI', ia_record[1])
    warc_headers.replace_header('WARC-Type', 'revisit')
    warc_headers.replace_header('WARC-Truncated', 'length')
    warc_headers.replace_header('WARC-Profile', 'http://netpreserve.org/warc/1.0/revisit/identical-payload-digest')
    warc_headers.remove_header('WARC-Block-Digest')
    warc_headers.remove_header('Content-Length')

    return writer.create_warc_record(
        record.rec_headers.get_header('WARC-Target-URI'),
        'revisit',
        warc_headers=warc_headers,
        http_headers=record.http_headers
    )

def process(filename_in, filename_out):
    with open(filename_in, 'rb') as file_in:
        with open(filename_out, 'wb') as file_out:
            writer = WARCWriter(filebuf=file_out, gzip=True)
            for record in ArchiveIterator(file_in):
                if record.rec_headers.get_header('WARC-Type') == 'response':
                    record_url = record.rec_headers.get_header('WARC-Target-URI')
                    record_digest = record.rec_headers.get_header('WARC-Payload-Digest')
                    ia_record = ia_available(record_url, record_digest)
                    #print(ia_record)
                    if not ia_record:
                        writer.write_record(record)
                    else:
                        print('Found duplicate, writing revisit record.')
                        writer.write_record(revisit_record(writer, record, ia_record))
                else:
                    writer.write_record(record)

if __name__ == '__main__':
    filename_in = sys.argv[1]
    filename_out = sys.argv[2]
    process(filename_in, filename_out)