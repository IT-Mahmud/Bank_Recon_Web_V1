# routes/bank_tally_reconcile_routes.py

from flask import Blueprint, request, jsonify
import pandas as pd
from sqlalchemy import text
from datetime import datetime

from utils.db import engine, ensure_table_exists
from logics.bank_tally_match_logic_mdb import match_cheques

bank_tally_bp = Blueprint('bank_tally_bp', __name__, url_prefix='/bank_tally')

@bank_tally_bp.route('/reconcile', methods=['POST'])
def reconcile_bank_tally():
    bank_code = request.form.get('bank_code')
    account_number = request.form.get('account_number')
    if not bank_code or not account_number:
        return jsonify({'success': False, 'msg': 'bank_code and account_number are required.'})

    try:
    
        # bank_df = pd.read_sql(
        #     text("SELECT * FROM bank_data WHERE is_matched = 0 AND acct_no=:acct_no"),
        #     engine, params={"acct_no": account_number}
        # )

        # tally_df = pd.read_sql(
        #     text("SELECT * FROM tally_data WHERE is_matched = 0 AND bank_code=:bank_code AND bank_acct_no=:acct_no"),
        #     engine, params={"bank_code": bank_code, "acct_no": account_number}
        #     )
    

        bank_df = pd.read_sql(
            text("SELECT * FROM bank_data WHERE bf_is_matched = 0 AND acct_no=:acct_no"),
            engine, params={"acct_no": account_number}
        )

        # tally_df = pd.read_sql(
        #     text("SELECT * FROM tally_data WHERE is_matched_bft = 0 AND bank_code=:bank_code AND bank_acct_no=:acct_no"),
        #     engine, params={"bank_code": bank_code, "acct_no": account_number}
        # )

        tally_df = pd.read_sql(
            text("SELECT * FROM tally_data WHERE is_matched_bft = 0 AND bank_code=:bank_code AND acct_no=:acct_no"),
            engine, params={"bank_code": bank_code, "acct_no": account_number}
        )
        # DEBUG PRINTS
        print("BTR BANK COLUMNS:", bank_df.columns.tolist())
        
        print("BTR TALLY COLUMNS:", tally_df.columns.tolist())

    except Exception as e:
        return jsonify({'success': False, 'msg': f'Error loading data: {e}'})

    if bank_df.empty or tally_df.empty:
        return jsonify({'success': False, 'msg': 'No unmatched data for this bank/account.'})

    # 2. Run your matching logic
    bt_matched = match_cheques(bank_df, tally_df, start_id=1)
    bt_matched_df = pd.DataFrame(bt_matched)
    print(bt_matched_df.columns.tolist())

    print("Columns in bt_matched_df:", bt_matched_df.columns.tolist())
    print(bt_matched_df.head(3))

    # 3. Save result to DB or return as needed
    ensure_table_exists(engine, 'bt_matched')
    bt_matched_df['input_date'] = datetime.now()

    # ---- Rename columns to match MySQL table names (with spaces) ----
    bt_matched_df = bt_matched_df.rename(columns={
        "Vch_Type": "Vch Type",
        "Vch_No_": "Vch No."
    })

    if not bt_matched_df.empty:
        bt_matched_df.to_sql('bt_matched', engine, if_exists='append', index=False)

    return jsonify({
        'success': True,
        'matched_count': len(bt_matched),
        'msg': f'Matched records inserted: {len(bt_matched)}'
    })
