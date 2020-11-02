#!/usr/bin/env python3

# Converts Triodos CSV export to YNAB4 CSV format.

# usage: triodos-to-ynab4.py Umsaetze_blah.CSV credit-ynab4.csv

import os
import sys
import csv
import locale
import re

# apparenty always EUR in Triodos, even for international transactions (they
# appear already converted)
#
# BUDGETCUR = 'EUR'

def strip_newlines(string):
    '''Replaces newlines (Unix or DOS) with colons.

Used because YNAB4 can't handle multi-line values in CSVs even if quoted.
    '''

    return re.sub(r'[\r\n]+', '; ', string)

LOCALE = 'de_DE.UTF-8'
locale.setlocale(locale.LC_NUMERIC, LOCALE)

if len(sys.argv) > 1:
    raw =  open(sys.argv[1], 'rt', encoding='iso-8859-1')
else:
    raw = sys.sdtdin
processed=[]

# first skip all the trash Triodos puts on top of the CSV file (u.u)
for line in raw:
    if not re.match(r'\s*[\'"]?Buchungstag[\'"]?\s*;', line):
        continue
    else:
        processed.append(line)
        break
for line in raw:
    processed.append(line)

if len(sys.argv) > 2:
    outf = open(sys.argv[2], 'wt', encoding='utf-8')
else:
    outf=sys.stdout

r = csv.DictReader(processed, delimiter=';')
w = csv.writer(outf, delimiter=',', quotechar='"')
w.writerow(['Date', 'Payee', 'Category', 'Memo', 'Outflow', 'Inflow'])

def get_payee_from_Vorgang(Vorgang):
    '''Extracts payee from the informational/memo/Vorgang field.

    In credit card transactions, the payer/payee etc. fields are coming empty.
    The payee apears to be bundled along with everything else as a text blob in
    the 'Vorgang/Verwendungszweck' column. This function tries to fetch it from there.
    '''

    lines = Vorgang.split("\n")
    if lines[0] in ('Lastschrift', 'Überweisungsgutschr.'):
        return lines[1]
    else:
        return None

for inrow in r:
    # for key in inrow.keys():
    #     print(key, inrow[key])
    # continue

    # skips dummy transactions
    if inrow['Kundenreferenz'] in ('Anfangssaldo', 'Endsaldo') \
       and not inrow['Vorgang/Verwendungszweck']: # sanity check just to be sure
        continue

    # magical empty header name lol
    # (it's the transaction type)
    if inrow[' '] == 'H':
        # Haben
        outflow = ''
        inflow = inrow['Umsatz']
    elif inrow[' '] == 'S':
        # Soll
        outflow = inrow['Umsatz']
        inflow = ''
    else:
        # does this ever happen?
        outflow = inrow['Umsatz']
        inflow = ''

    memo = inrow['Vorgang/Verwendungszweck']
    # attach all the extra fields to YNAB4 memo field
    for key in ('Kundenreferenz', 'Valuta', 'Konto-Nr.', 'IBAN', 'BLZ', 'BIC'):
        if inrow[key]:
            memo += "; %s: %s" % (key, inrow[key])

    payee = inrow['Empfänger/Zahlungspflichtiger']
    if not payee:
        payee = get_payee_from_Vorgang(inrow['Vorgang/Verwendungszweck'])

    outrow = [
        inrow['Buchungstag'].replace('.', '/'),
        payee or '?', # payee; shouldn't be empty
        '', # category,
        memo,
        outflow,
        inflow,
    ]

    w.writerow([strip_newlines(field) for field in outrow])
