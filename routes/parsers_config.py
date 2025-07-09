# routes/parsers_config.py

from parsers.fin_parser import parse_fin_statement
from parsers.mdb_parser import parse_mdb_statement
from parsers.mtb_parser import parse_mtb_statement
from parsers.tally_parser import parse_tally_file

PARSERS = [
    {
        'id': 'finance',
        'title': 'Finance Paid List Parser',
        'file_field': 'finance_file',
        'route': '/parse_finance',
        'parse_func': parse_fin_statement,
        'table': 'fin_data',
    },
    {
        'id': 'bank',
        'title': 'Bank Statement Parser',
        'file_field': 'bank_file',
        'route': '/parse_bank',
        'parse_func': None,
        'table': None,
    },
    {
        'id': 'tally',
        'title': 'Tally Parser',
        'file_field': 'tally_file',
        'route': '/parse_tally',
        'parse_func': parse_tally_file,
        'table': 'tally_data',
    }
]
