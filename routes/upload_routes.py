import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from utils.db import engine, ensure_table_exists
from routes.parsers_config import PARSERS
from parsers.fin_parser import parse_fin_statement
from parsers.mdb_parser import parse_mdb_statement
from parsers.mtb_parser import parse_mtb_statement
from parsers.tally_parser import parse_tally_file

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

upload_bp = Blueprint('upload', __name__)

# A dictionary that maps each bank to the allowed statement file types
BANK_FILE_EXTENSIONS = {
    'MDB': ['.xlsx'],   # Only .xlsx for MDB
    'MTB': ['.xls'],    # Only .xls for MTB
    'EBL': [],
    'OBL': [],
    'IBBL': [],
    # Add more banks here as needed
}

def generic_parse(parse_func, table, file_field):
    file = request.files.get(file_field)
    sheet_name = request.form.get('sheet_name')
    msg = ""
    uploaded_filename = None

    if not file or not sheet_name:
        return jsonify({'success': False, 'msg': 'File or sheet not provided.'})

    filename = secure_filename(file.filename)
    temp_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(temp_path)

    try:
        df_data = parse_func(temp_path, sheet_name=sheet_name)
        df_data["input_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ensure_table_exists(engine, table)

        if table == 'tally_data' and 'mdb_acct_no' in df_data.columns:
            df_data = df_data.rename(columns={'mdb_acct_no': 'acct_no'})

        df_data.to_sql(table, engine, if_exists='append', index=False)
        uploaded_filename = filename
        msg = f"✅ Successfully uploaded and parsed data from sheet: {sheet_name}"
        success = True
    except IntegrityError as e:
        db_error = str(e.orig) if hasattr(e, 'orig') else str(e)
        msg = (
            f"❌ Upload failed due to a database error:\n"
            f"{db_error}\n\n"
            f"Tip: This usually means there are duplicate or blank unique IDs in your upload file, "
            f"or that the same IDs already exist in the database. "
            f"Please check your file and try again."
        )
        success = False
    except Exception as e:
        msg = f"❌ Error during parsing or DB insert: {e}"
        success = False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return jsonify({'success': success, 'msg': msg, 'uploaded_filename': uploaded_filename})

@upload_bp.route('/parse_finance', methods=['POST'])
def parse_finance():
    return generic_parse(parse_func=parse_fin_statement, table='fin_data', file_field='finance_file')

@upload_bp.route('/parse_tally', methods=['POST'])
def parse_tally():
    return generic_parse(parse_func=parse_tally_file, table='tally_data', file_field='tally_file')

@upload_bp.route('/parse_bank', methods=['POST'])
def parse_bank():
    file = request.files.get('bank_file')
    bank_name = request.form.get('bank_name')
    sheet_name = request.form.get('sheet_name', None)
    msg = ""
    uploaded_filename = None

    if not file:
        return jsonify({'success': False, 'msg': 'File not provided.'})

    if not bank_name:
        return jsonify({'success': False, 'msg': 'Bank name not selected.'})

    # Retrieve the allowed extensions for the selected bank from the dictionary
    allowed_extensions = BANK_FILE_EXTENSIONS.get(bank_name, [])
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[-1].lower()

    # Check if the file extension is allowed for the selected bank
    if file_ext not in allowed_extensions:
        return jsonify({'success': False, 'msg': f'Unsupported file type for {bank_name}. Allowed types: {", ".join(allowed_extensions)}'})

    temp_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(temp_path)

    try:
        # Now insert data into 'bank_data' table instead of specific bank tables
        if bank_name == 'MDB':
            df_data = parse_mdb_statement(temp_path)
        elif bank_name == 'MTB':
            df_data = parse_mtb_statement(temp_path)
        elif bank_name == 'EBL':
            raise Exception("Parsing for Eastern Bank (EBL) is not implemented yet.")
        elif bank_name == 'OBL':
            raise Exception("Parsing for One Bank (OBL) is not implemented yet.")
        elif bank_name == 'IBBL':
            raise Exception("Parsing for Islami Bank (IBBL) is not implemented yet.")
        else:
            raise Exception("Selected bank is not recognized.")

        # Insert all data into 'bank_data' table
        df_data["input_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ensure_table_exists(engine, 'bank_data')  # Ensures the 'bank_data' table exists
        df_data.to_sql('bank_data', engine, if_exists='append', index=False)  # Insert all data into 'bank_data'

        uploaded_filename = filename
        msg = f"✅ Successfully uploaded and parsed data for {bank_name}"
        success = True
    except IntegrityError as e:
        db_error = str(e.orig) if hasattr(e, 'orig') else str(e)
        msg = (
            f"❌ Upload failed due to a database error:\n"
            f"{db_error}\n\n"
            f"Tip: This usually means there are duplicate or blank unique IDs in your upload file, "
            f"or that the same IDs already exist in the database. "
            f"Please check your file and try again."
        )
        success = False
    except Exception as e:
        msg = f"❌ Error during parsing or DB insert: {e}"
        success = False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify({'success': success, 'msg': msg, 'uploaded_filename': uploaded_filename})
