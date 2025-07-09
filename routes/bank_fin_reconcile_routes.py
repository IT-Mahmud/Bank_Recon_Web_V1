# routes/bank_fin_reconcile_routes.py

from flask import Blueprint, request, jsonify
import pandas as pd
from sqlalchemy import text
from datetime import datetime

from utils.db import engine, ensure_table_exists
from logics.bank_fin_match_logic import bank_fin_match, flatten_bf_matches

bank_fin_reconcile_bp = Blueprint('bank_fin_reconcile', __name__)


@bank_fin_reconcile_bp.route('/get_accounts', methods=['POST'])
def get_accounts():
    acct_col = 'acct_no'
    bank_code = request.form.get('bank_code')

    try:
        df = pd.read_sql("SELECT * FROM bank_data", engine)
        if bank_code:
            df = df[df['bank_code'] == bank_code]
        if acct_col in df.columns:
            acct_no_list = sorted(df[acct_col].dropna().astype(str).unique())
        else:
            acct_no_list = []
        return jsonify({'success': True, 'accounts': acct_no_list})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})


@bank_fin_reconcile_bp.route('/reconcile', methods=['POST'])
def reconcile():
    account_number = request.form.get('account_number')
    fin_table = 'fin_data'  # Always the same, universal
    bank_code = request.form.get('bank_code')
    if not bank_code:
        return jsonify({'success': False, 'msg': 'bank_code is required.'})

    try:
        bank_df = pd.read_sql(
            "SELECT * FROM bank_data WHERE bf_is_matched = 0", engine)
        if 'bank_code' in bank_df.columns:
            bank_df = bank_df[bank_df['bank_code'] == bank_code]

        fin_df = pd.read_sql(
            f"SELECT * FROM {fin_table} WHERE bf_is_matched = 0", engine)

        acct_col = 'acct_no'
        if account_number and acct_col in bank_df.columns:
            bank_df = bank_df[bank_df[acct_col].astype(
                str) == str(account_number)]

        # Find the first account number (for run_tag)
        acct_no = None
        if acct_col in bank_df.columns:
            values = bank_df[acct_col].dropna().astype(str)
            if not values.empty:
                acct_no = values.iloc[0]
        if not acct_no:
            acct_no = "UnknownAcct"

    except Exception as e:
        return jsonify({'success': False, 'msg': f'Error loading tables: {e}'})

    run_tag = f"{bank_code}_{acct_no}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    BANK_CONFIG = {
        'MDB': {
            'date_col': 'B_Date',
            'particular_col': 'B_Particulars',
            'debit_col': 'B_Withdrawal',
            'credit_col': 'B_Deposit',
            'balance_col': 'B_Balance',
            'bank_uid_col': 'bank_uid',
            'bank_ven_col': 'bank_ven',
        },
        'MTB': {
            'date_col': 'B_Date',
            'particular_col': 'B_Particulars',
            'ref_col': 'B_Ref_Cheque',
            'debit_col': 'B_Withdrawal',
            'credit_col': 'B_Deposit',
            'balance_col': 'B_Balance',
            'bank_uid_col': 'bank_uid',
            'bank_ven_col': 'bank_ven',
        }
        # Add more banks here if needed
    }

    config = BANK_CONFIG.get(bank_code)
    if not config:
        return jsonify({'success': False, 'msg': f'Unsupported bank code: {bank_code}.'})

    try:
        matched_rows, unmatched_bank, unmatched_finance = bank_fin_match(
            bank_df, fin_df, config, bank_code)

        matched_bank_ids = []
        matched_fin_ids = []
        for row in matched_rows:
            if row['source'] == 'Bank' and row.get('bank_id') is not None:
                matched_bank_ids.append(int(row['bank_id']))
            elif row['source'] == 'Finance' and row.get('fin_id') is not None:
                matched_fin_ids.append(int(row['fin_id']))

        matched_bank_ids = list(set(matched_bank_ids))
        matched_fin_ids = list(set(matched_fin_ids))


        # --------- Build bf_matched_df BEFORE dropping columns ---------
        bank_cols = list(bank_df.columns)
        fin_cols = list(fin_df.columns)
        bf_matched_df = flatten_bf_matches(
            matched_rows, bank_cols, fin_cols, run_tag=run_tag)
        bf_matched_df['bank_code'] = bank_code
        # bf_matched_df['date_matched'] = datetime.now()
        bf_matched_df['bf_date_matched'] = datetime.now()

        # Drop helper columns if present
        helper_cols = [
            '_vendor_first5', '_ven_alias', '_norm_amt', '_norm_date',
            # add any other temp/helper columns you use here
        ]
        bf_matched_df = bf_matched_df.drop(columns=[c for c in helper_cols if c in bf_matched_df], errors='ignore')

        ensure_table_exists(engine, 'bf_matched')

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with engine.begin() as conn:
            # 1. Insert bf_matched rows first, atomically
            if not bf_matched_df.empty:
                bf_matched_df["bf_is_matched"] = 1
                bf_matched_df.to_sql('bf_matched', conn, if_exists='append', index=False)
            # 2. Update is_matched status for matched bank rows
            if matched_bank_ids:
                ids_str = ','.join(map(str, matched_bank_ids))
                conn.execute(text(
                    f"UPDATE bank_data SET bf_is_matched=1, bf_date_matched=:dt WHERE bank_id IN ({ids_str})"), {"dt": now_str})
            if matched_fin_ids:
                ids_str = ','.join(map(str, matched_fin_ids))
                conn.execute(text(
                    f"UPDATE {fin_table} SET bf_is_matched=1, bf_date_matched=:dt WHERE fin_id IN ({ids_str})"), {"dt": now_str})


        return jsonify({
            'success': True,
            'matched_count': len(matched_rows),
            'unmatched_bank_count': len(unmatched_bank),
            'unmatched_finance_count': len(unmatched_finance),
            'run_tag': run_tag,
            'inserted_to_table': len(bf_matched_df)
        })
    except Exception as e:
        return jsonify({'success': False, 'msg': f'Error during reconciliation: {e}'})
