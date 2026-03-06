#!/usr/bin/env python3
"""
Email Helper - IMAP/SMTP wrapper for reading and sending emails
Usage:
  python3 email_helper.py list [--account arkady] [--folder INBOX] [--limit 10]
  python3 email_helper.py read <uid> [--account arkady]
  python3 email_helper.py send --to <email> --subject <subject> --body <text> [--account arkady]
"""

import imaplib
import smtplib
import email
import sys
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email import policy
from datetime import datetime
import os
import mimetypes

# Account configurations
ACCOUNTS = {
    'arkady': {
        'email': 'a.parmeev@jakeberrimor.com',
        'password': os.getenv('ARKADY_PASSWORD', 'vL0pG4oD5zmU4iE2'),
        'imap': {'host': 'mail.jakeberrimor.com', 'port': 993},
        'smtp': {'host': 'mail.jakeberrimor.com', 'port': 465},
    },
    'dparmeev': {
        'email': 'dparmeev@luminesfox.com',
        'password': os.getenv('DPARMEEV_PASSWORD', ''),
        'imap': {'host': 'mail.hosting.reg.ru', 'port': 993},
        'smtp': {'host': 'mail.hosting.reg.ru', 'port': 465},
    },
}

def list_emails(account='arkady', folder='INBOX', limit=10):
    """List recent emails"""
    config = ACCOUNTS[account]
    
    mail = imaplib.IMAP4_SSL(config['imap']['host'], config['imap']['port'])
    mail.login(config['email'], config['password'])
    mail.select(folder)
    
    # Search for today's emails
    status, messages = mail.search(None, 'ALL')
    message_ids = messages[0].split()
    
    print(f"Total emails in {folder}: {len(message_ids)}")
    print(f"\nShowing last {limit} emails:\n")
    
    # Get last N emails
    for msg_id in message_ids[-limit:]:
        status, msg_data = mail.fetch(msg_id, '(BODY.PEEK[HEADER])')
        email_msg = email.message_from_bytes(msg_data[0][1], policy=policy.default)
        
        uid = msg_id.decode()
        subject = email_msg.get('Subject', 'No Subject')
        from_addr = email_msg.get('From', 'Unknown')
        date = email_msg.get('Date', 'Unknown')
        
        print(f"UID: {uid}")
        print(f"From: {from_addr}")
        print(f"Date: {date}")
        print(f"Subject: {subject}")
        print("-" * 80)
    
    mail.close()
    mail.logout()

def read_email(uid, account='arkady', folder='INBOX'):
    """Read a specific email by UID"""
    config = ACCOUNTS[account]
    
    mail = imaplib.IMAP4_SSL(config['imap']['host'], config['imap']['port'])
    mail.login(config['email'], config['password'])
    mail.select(folder)
    
    status, msg_data = mail.fetch(str(uid).encode(), '(RFC822)')
    email_msg = email.message_from_bytes(msg_data[0][1], policy=policy.default)
    
    print(f"From: {email_msg.get('From')}")
    print(f"To: {email_msg.get('To')}")
    print(f"Subject: {email_msg.get('Subject')}")
    print(f"Date: {email_msg.get('Date')}")
    print("\n--- BODY ---\n")
    
    # Extract text
    if email_msg.is_multipart():
        for part in email_msg.walk():
            if part.get_content_type() == "text/plain":
                print(part.get_content())
                break
            elif part.get_content_type() == "text/html":
                # Fallback to HTML if no plain text
                print("[HTML content - showing raw]")
                print(part.get_content()[:1000])
                break
    else:
        print(email_msg.get_content())
    
    # List attachments
    if email_msg.is_multipart():
        attachments = [p for p in email_msg.walk() if p.get_content_disposition() == 'attachment']
        if attachments:
            print(f"\n--- ATTACHMENTS ({len(attachments)}) ---")
            for att in attachments:
                print(f"- {att.get_filename()}")
    
    mail.close()
    mail.logout()

def send_email(to, subject, body, account='arkady', cc=None, attachments=None, html=None):
    """Send an email"""
    config = ACCOUNTS[account]
    
    msg = MIMEMultipart('mixed')
    msg['From'] = config['email']
    msg['To'] = to
    msg['Subject'] = subject
    if cc:
        msg['Cc'] = cc
    
    # Create alternative part for text/html
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    
    # Add plain text version
    msg_alternative.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Add HTML version if provided
    if html:
        msg_alternative.attach(MIMEText(html, 'html', 'utf-8'))
    
    # Add attachments
    if attachments:
        for filepath in attachments:
            if not os.path.exists(filepath):
                print(f"Warning: attachment not found: {filepath}")
                continue
            
            filename = os.path.basename(filepath)
            
            # Guess MIME type
            ctype, encoding = mimetypes.guess_type(filepath)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            
            with open(filepath, 'rb') as f:
                part = MIMEBase(maintype, subtype)
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)
            
            print(f"  + Attached: {filename}")
    
    server = smtplib.SMTP_SSL(config['smtp']['host'], config['smtp']['port'])
    server.login(config['email'], config['password'])
    
    recipients = [to]
    if cc:
        recipients.extend(cc.split(','))
    
    server.send_message(msg)
    server.quit()
    
    print(f"✅ Email sent to {to}")

def main():
    parser = argparse.ArgumentParser(description='Email Helper - IMAP/SMTP wrapper')
    parser.add_argument('command', choices=['list', 'read', 'send'], help='Command to execute')
    parser.add_argument('--account', default='arkady', help='Email account')
    parser.add_argument('--folder', default='INBOX', help='IMAP folder')
    parser.add_argument('--limit', type=int, default=10, help='Number of emails to list')
    parser.add_argument('uid', nargs='?', help='Email UID (for read command)')
    parser.add_argument('--to', help='Recipient email (for send command)')
    parser.add_argument('--subject', help='Email subject (for send command)')
    parser.add_argument('--body', help='Email body (for send command)')
    parser.add_argument('--html', help='HTML body (for send command)')
    parser.add_argument('--cc', help='CC recipients (comma-separated)')
    parser.add_argument('--attach', action='append', help='File to attach (can be used multiple times)')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'list':
            list_emails(account=args.account, folder=args.folder, limit=args.limit)
        elif args.command == 'read':
            if not args.uid:
                print("Error: UID required for read command")
                sys.exit(1)
            read_email(args.uid, account=args.account, folder=args.folder)
        elif args.command == 'send':
            if not all([args.to, args.subject, args.body]):
                print("Error: --to, --subject, and --body required for send command")
                sys.exit(1)
            send_email(args.to, args.subject, args.body, account=args.account, cc=args.cc, html=args.html, attachments=args.attach)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
