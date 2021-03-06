#!/usr/bin/env python
#
# Very basic example of using Python and IMAP to iterate over emails in a
# gmail folder/label.  This code is released into the public domain.
#
# RKI July 2013
# http://www.voidynullness.net/blog/2013/07/25/gmail-email-with-python-via-imap/
#

"""This module implements an email parser to access targeted info."""

import sys
import imaplib
import email
import datetime
import account
import base64
import os
from email.Parser import Parser as EmailParser
from StringIO import StringIO

EMAIL_FOLDER = "INBOX"

# ======================================================
# Sample Implementations of Email parser
# ======================================================


def process_mailbox(M):
    """.

    Do something with emails messages in the folder.
    For the sake of this example, print some headers.
    """
    rv, data = M.search(None, "ALL")
    if rv != 'OK':
        print "No messages found!"
        return

    ids = data[0]
    id_list = ids.split()
    for num in id_list:
        rv, data = M.fetch(num, '(RFC822)')
        if rv != 'OK':
            print "ERROR getting message", num
            return

        msg = email.message_from_string(data[0][1])
        decode = email.header.decode_header(msg['Subject'])[0]
        subject = unicode(decode[0])
        print 'Message %s: %s' % (num, subject)
        print 'Raw Date:', msg['Date']
        # Now convert to local date-time
        date_tuple = email.utils.parsedate_tz(msg['Date'])
        if date_tuple:
            local_date = datetime.datetime.fromtimestamp(
                email.utils.mktime_tz(date_tuple))
            print "Local Date:", \
                local_date.strftime("%a, %d %b %Y %H:%M:%S")


def get_latest_email(M):
    """.

    get the most recent received email.
    """
    data = search_email_by_time(M)
    if data is None:
        return
    print "Access data succeed"
    print "Got data as ", data
    ids = data[0]
    id_list = ids.split()
    if len(id_list) > 0:
        latest_email_id = id_list[-1]
        # search unique id
        rv, data = M.uid('fetch', latest_email_id, "(RFC822)")
        if rv != "OK":
            print "Error getting message"
            return
        # here's the body, which is raw text of the whole email
        # including headers and alternate payloads
        raw_email = data[0][1]
        print "raw_email is ", raw_email
        # print raw_email
        email_message = email.message_from_string(raw_email)
        print "To: ", email_message['To'], "\n"
        print "From: ", email.utils.parseaddr(email_message['From']), "\n"
        # print all headers
        # print email_message.items(), "\n"

        # print the body text
        print get_first_text_block(email_message)


def get_first_text_block(email_message_instance):
    """.

    retrieve the text block in the email body
    """
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return email_message_instance.get_payload()


def search_email_by_all(M):
    """.

    basic search mode, search all
    """
    print "basic search mode\n"
    rv, data = M.uid('search', None, 'All')
    if check_response(rv):
        return data
    else:
        return None


def search_email_by_time(M):
    """.

    search email by time
    """
    print "search mail by time\n"
    date = (datetime.date.today() - datetime.timedelta(1)).strftime("%d-%b-%Y")
    rv, data = M.uid('search', None, '(SENTSINCE {date})'.format(date=date))
    if check_response(rv):
        return data
    else:
        return None

# ======================================================
# Actual Implementations of Email parser
# ======================================================


def get_group_of_emails(M):
    """Get a group of emails.

    This function will access emails from a group of contacts.
    """
    print "Try to access group of emails"
    data = search_email_advanced(M)
    if data is None:
        return
    # print "Got data as ", data
    ids = data[0]
    id_list = ids.split()
    for id_num in id_list:
        rv, data = M.uid('fetch', id_num, "(RFC822)")
        if rv != "OK":
            print "Error getting message"
            return
        # get raw text of the whole email
        raw_email = data[0][1]
        content = email.message_from_string(raw_email)
        # print raw_email
        p = EmailParser()
        # print sender and receivers
        print "To: ", content['To'], "\n"
        print "From: ", email.utils.parseaddr(content['From']), "\n"
        print "Date: ", content['Date'], "\n"
        print "Subject: ", p.parsestr(raw_email).get('Subject'), \
            "\n"
        result = parse_content(content)
        # print results
        printData(result)


def parse_content(content):
    """Get body text from a email.

    return the body.
    """
    attachments = []
    body = None
    html = None

    for part in content.walk():
        if part.get('Content-Disposition') is not None:
            decoded_data = decode_attachment(part)

        attachment = parse_attachment(part)
        if attachment:
            attachments.append(attachment)
        elif part.get_content_type() == "text/plain":
            if body is None:
                body = ""
            body += unicode(
                part.get_payload(decode=True),
                part.get_content_charset(),
                'replace'
                ).encode('utf8', 'replace')
        elif part.get_content_type() == "text/html":
            if html is None:
                html = ""
            html += unicode(
                part.get_payload(decode=True),
                part.get_content_charset(),
                'replace'
            ).encode('utf8', 'replace')
    # return the parsed data
    return {
        'body': body,
        'html': html,
        'filename': decoded_data['filename']
        # 'attachments': attachments
    }


def decode_attachment(attachment, download_folder='convert_pdf/downloads'):
    """Decode attachment string by base64.

    Return the decoded string and filename
    """
    filename = attachment.get_filename()
    # get downloads directory path for attachment
    att_path = os.path.join(download_folder, filename)

    if not os.path.isfile(att_path):
        fp = open(att_path, 'wb')
        fp.write(attachment.get_payload(decode=True))
        fp.close()

    # create two output files used to compare decoded string
    # out1 = open('with_newline.out', 'wb')
    # out0 = open('without_newline.out', 'wb')

    with open(att_path, 'r') as attachfile:
        data1 = base64.b64decode(attachfile.read())

    # with open(att_path, 'r') as attachfile:
    #    data0 = base64.b64decode(attachfile.read().replace('\n', ''))
    # Redirect the output
    # out1.write(data1)
    # out0.write(data0)
    # Close files
    # out1.close()
    # out0.close()
    return {
        'filename': filename,
        'decoded_string': data1
    }


def parse_attachment(message_part):
    """Parse Email Attachment.

    parse attachment.
    """
    content_disposition = message_part.get("Content-Disposition", None)
    if content_disposition:
        dispositions = content_disposition.strip().split(";")
        if bool(content_disposition and
                dispositions[0].lower() == "attachment"):

                file_data = message_part.get_payload(decode=True)
                attachment = StringIO(file_data)
                attachment.content_type = message_part.get_content_type()
                attachment.size = len(file_data)
                attachment.name = None
                attachment.create_date = None
                attachment.mod_date = None
                attachment.read_date = None

                for param in dispositions[1:]:
                    name, value = param.split("=")
                    name = name.lower()

                    if name == "filename":
                        attachment.name = value
                    elif name == "create-date":
                        attachment.create_date = value  # TODO: datetime
                    elif name == "modification-date":
                        attachment.mod_date = value  # TODO: datetime
                    elif name == "read-date":
                        attachment.read_date = value  # TODO: datetime
                return attachment
    # no attachment
    return None


def printData(result):
    """Print parsed info.

    simple print statements.
    """
    print "Body: \n", result['body']
    print "Html: \n", result['html']
    print "Attachment: \n", result['filename']
    # print "Attachments: \n", result['attachments']


def search_email_advanced(M):
    """.

    limit search by date, subject, and exclude a sender
    """
    print "\n=============================="
    print "Search emails in advanced mode"
    print "==============================\n"

    till_date = 50
    date_range = datetime.date.today() - datetime.timedelta(till_date)
    date = date_range.strftime("%d-%b-%Y")
    # rv, data = M.uid('search', None, \
    #    '(SENTSINCE {date} FROM "lmxvip@hotmail.com")'.format(date=date))
    rv, data = M.uid(
        'search',
        None,
        '(SENTSINCE {date} FROM "cindyyueweiluo@gmail.com")'
        .format(date=date)
        )
    if check_response(rv):
        return data
    else:
        return None


def check_response(rv):
    """.

    check whether response is OK or not
    return true if it's OK
    return false otherwise.
    """
    if rv != 'OK':
        print "No message found"
        return False
    return True

# ======================================================
# Running Program
# ======================================================
# try to log into account
M = imaplib.IMAP4_SSL('imap.gmail.com')

try:
    rv, data = M.login(account.EMAIL_ACCOUNT, account.EMAIL_PSS)
except imaplib.IMAP4.error:
    print "LOGIN FAILED!!! "
    sys.exit(1)

print rv, data

rv, mailboxes = M.list()
if rv == 'OK':
    print "Mailboxes:"
    print mailboxes

rv, data = M.select(EMAIL_FOLDER)
if rv == 'OK':
    print "Processing mailbox INBOX...\n"
    get_group_of_emails(M)
    M.close()
else:
    print "ERROR: Unable to open mailbox ", rv

M.logout()
