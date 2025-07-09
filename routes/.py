# routes/bank_fin_tally_reconcile_routes.py

from flask import Blueprint, request, jsonify
import pandas as pd
from sqlalchemy import text
from datetime import datetime

from utils.db import engine, ensure_table_exists
from logics.bank_fin_tally_match_logic import bank_fin_tally_match

bank_fin_tally_reconcile_bp = Blueprint('bank_fin_tally_reconcile', __name__)

@bank_fin_tally_reconcile_bp.route('/get_bft_accounts', methods=['POST'])
def get_bft_accounts():
    bank_code = request.form.get('bank_code')
    if not bank_code:
        return jsonify({'success': False, 'msg': 'bank_code is required.'})
    try:
        # Only get account numbers from unmatched bank rows
        df = pd.read_sql(
            text("SELECT DISTINCT acct_no FROM bf_matched WHERE is_matched_bft=0 "
                "AND bank_code=:bank_code AND LOWER(bf_source) = 'bank'"),
            engine, params={"bank_code": bank_code}
        )
        accts = sorted(df['acct_no'].dropna().astype(str).unique()) if not df.empty else []



        return jsonify({'success': True, 'accounts': accts})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@bank_fin_tally_reconcile_bp.route('/reconcile_bft', methods=['POST'])
@bank_fin_tally_reconcile_bp.route('/reconcile_bft', methods=['POST'])
def reconcile_bft():
    bank_code = request.form.get('bank_code')
    account_number = request.form.get('account_number')
    if not bank_code or not account_number:
        return jsonify({'success': False, 'msg': 'bank_code and account_number are required.'})

    try:
        # 1. Find all bf_match_id's for this bank/account (from BANK rows only)
        # group_ids_df = pd.read_sql(
        #     text("SELECT DISTINCT bf_match_id FROM bf_matched WHERE is_matched_bft=0 "
        #          "AND bank_code=:bank_code AND Bank_acct_no=:account_number AND LOWER(bf_source) = 'bank'"),
        #     engine, params={"bank_code": bank_code, "account_number": account_number}
        # )

        group_ids_df = pd.read_sql(
            text("SELECT DISTINCT bf_match_id FROM bf_matched WHERE is_matched_bft=0 "
                "AND bank_code=:bank_code AND acct_no=:account_number AND LOWER(bf_source) = 'bank'"),
            engine, params={"bank_code": bank_code, "account_number": account_number}
        )


        group_ids = group_ids_df['bf_match_id'].tolist()

        if not group_ids:
            return jsonify({'success': False, 'msg': 'No groups found for this bank/account.'})

        # 2. Fetch ALL records for those group ids (bank + finance)
        placeholders = ', '.join([f"'{gid}'" for gid in group_ids])
        sql = f"SELECT * FROM bf_matched WHERE is_matched_bft=0 AND bf_match_id IN ({placeholders})"
        bf_df = pd.read_sql(
            sql,
            engine
        )

        # 3. Fetch Tally records (filtered by bank/account)
        # tally_df = pd.read_sql(
        #     text("SELECT * FROM tally_data WHERE is_matched_bft=0 "
        #          "AND bank_code=:bank_code AND bank_acct_no=:account_number"),
        #     engine, params={"bank_code": bank_code, "account_number": account_number}
        # )


        tally_df = pd.read_sql(
            text("SELECT * FROM tally_data WHERE is_matched_bft=0 "
                "AND bank_code=:bank_code AND acct_no=:account_number"),
            engine, params={"bank_code": bank_code, "account_number": account_number}
        )

    except Exception as e:
        return jsonify({'success': False, 'msg': f'Error loading tables: {e}'})

    if bf_df.empty or tally_df.empty:
        return jsonify({
            'success': False,
            'msg': 'No unmatched bf_matched or tally_data found for this bank/account.',
            'matched_count': 0,
            'unmatched_bf_count': bf_df.shape[0] if not bf_df.empty else 0,
            'unmatched_tally_count': tally_df.shape[0] if not tally_df.empty else 0
        })

    # Matching logic
    bft_matched_df = bank_fin_tally_match(bf_df, tally_df, bank_code)

    ensure_table_exists(engine, 'bft_matched')
    inserted_count = 0

    matched_bank_count = 0
    matched_tally_count = 0

    # if not bft_matched_df.empty:
    #     # Only keep columns that exist in bft_matched table (from your schema)
    #     actual_cols = [
    #         'bft_match_id', 'bft_source', 'bft_match_type', 'date_matched', 'bf_match_id', 'bf_source', 'bf_match_type',
    #         'bank_code', 'Bank_id', 'Bank_bank_uid', 'Bank_Date', 'Bank_Particular', 'Bank_Withdrawal', 'Bank_Deposit', 'Bank_Balance',
    #         'Bank_bank_ven', 'Bank_acct_no', 'Bank_Transaction Detail', 'Bank_Ref/Cheque No', 'Bank_Withdrawal (Dr.)', 'Bank_Deposit (Cr.)',
    #         'Bank_Branch', 'Fin_id', 'Fin_fin_uid', 'Fin_Credit Amount', 'Fin_Receiver Name', 'Fin_Bank Name', 'Fin_Branch Name',
    #         'Fin_Sender Name', 'Fin_Sender Account', 'Fin_Sender Bank', 'Fin_Unit Name', 'Fin_Team Name', 'Fin_Project', 'Fin_PO',
    #         'Fin_Status', 'Fin_Voucher Date', 'Fin_Voucher No', 'Fin_Payment Date', 'Fin_Remarks', 'tally_uid', 'Vch No.', 'Vch Type',
    #         'Date', 'Particulars', 'Debit', 'Credit', 'tally_ven', 'statement_month', 'statement_year', 'input_date'
    #     ]
    #     # Add/update input_date just before insert
    #     bft_matched_df['input_date'] = datetime.now()
    #     # Filter DataFrame to actual columns
    #     bft_matched_df = bft_matched_df[[col for col in actual_cols if col in bft_matched_df.columns]]
    #     bft_matched_df.to_sql('bft_matched', engine, if_exists='append', index=False)
    #     inserted_count = len(bft_matched_df)

    # if not bft_matched_df.empty:
    #     # Add/update input_date just before insert
    #     bft_matched_df['input_date'] = datetime.now()
    #     # Drop helper columns (if you use any, e.g. temp columns starting with _)
    #     helper_cols = [
    #         '_vendor_first5', '_ven_alias', '_norm_amt', '_norm_date',
    #         # add any other temp/helper columns you use here
    #     ]
    #     bft_matched_df = bft_matched_df.drop(columns=[c for c in helper_cols if c in bft_matched_df], errors='ignore')
    #     # Drop 'id' column if present (to avoid PK conflicts)
    #     if 'id' in bft_matched_df.columns:
    #         bft_matched_df = bft_matched_df.drop(columns=['id'])
    #     bft_matched_df.to_sql('bft_matched', engine, if_exists='append', index=False)
    #     inserted_count = len(bft_matched_df)

    #     # Count matched bank and tally rows in this batch
    #     matched_bank_count = bft_matched_df[bft_matched_df['bft_source'] == 'Bank'].shape[0]
    #     matched_tally_count = bft_matched_df[bft_matched_df['bft_source'] == 'Tally'].shape[0]

    #     matched_bf_ids = bft_matched_df.loc[bft_matched_df['bft_source'] == 'Bank', 'bf_match_id'].unique().tolist()
    #     matched_tally_uids = bft_matched_df.loc[bft_matched_df['bft_source'] == 'Tally', 'tally_uid'].unique().tolist()
    #     now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #     with engine.begin() as conn:
    #         if matched_bf_ids:
    #             ids = ",".join(f"'{x}'" for x in matched_bf_ids)
    #             conn.execute(text(
    #                 f"UPDATE bf_matched SET is_matched_bft=1, date_matched_bft=:dt "
    #                 f"WHERE bf_match_id IN ({ids})"
    #             ), {"dt": now_str})
    #         if matched_tally_uids:
    #             uids = ",".join(f"'{x}'" for x in matched_tally_uids)
    #             conn.execute(text(
    #                 f"UPDATE tally_data SET is_matched_bft=1, date_matched_bft=:dt "
    #                 f"WHERE tally_uid IN ({uids})"
    #             ), {"dt": now_str})
    if not bft_matched_df.empty:
        bft_matched_df['input_date'] = datetime.now()
        helper_cols = [
            '_vendor_first5', '_ven_alias', '_norm_amt', '_norm_date',
            # add any other temp/helper columns you use here
        ]
        bft_matched_df = bft_matched_df.drop(columns=[c for c in helper_cols if c in bft_matched_df], errors='ignore')
        if 'id' in bft_matched_df.columns:
            bft_matched_df = bft_matched_df.drop(columns=['id'])

        matched_bank_count = 0
        matched_tally_count = 0

        matched_bf_ids = []
        matched_tally_uids = []
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Begin atomic transaction for insert and updates
        with engine.begin() as conn:
            bft_matched_df.to_sql('bft_matched', conn, if_exists='append', index=False)
            inserted_count = len(bft_matched_df)

            matched_bank_count = bft_matched_df[bft_matched_df['bft_source'] == 'Bank'].shape[0]
            matched_tally_count = bft_matched_df[bft_matched_df['bft_source'] == 'Tally'].shape[0]

            matched_bf_ids = bft_matched_df.loc[bft_matched_df['bft_source'] == 'Bank', 'bf_match_id'].unique().tolist()
            matched_tally_uids = bft_matched_df.loc[bft_matched_df['bft_source'] == 'Tally', 'tally_uid'].unique().tolist()

            if matched_bf_ids:
                ids = ",".join(f"'{x}'" for x in matched_bf_ids)
                conn.execute(text(
                    f"UPDATE bf_matched SET is_matched_bft=1, date_matched_bft=:dt "
                    f"WHERE bf_match_id IN ({ids})"
                ), {"dt": now_str})
            if matched_tally_uids:
                uids = ",".join(f"'{x}'" for x in matched_tally_uids)
                conn.execute(text(
                    f"UPDATE tally_data SET is_matched_bft=1, date_matched_bft=:dt "
                    f"WHERE tally_uid IN ({uids})"
                ), {"dt": now_str})




    # Calculate unmatched counts
    total_bank_rows = bf_df[bf_df['bf_source'].str.lower() == 'bank'].shape[0]
    total_tally_rows = tally_df.shape[0]
    unmatched_bf_count = total_bank_rows - matched_bank_count
    unmatched_tally_count = total_tally_rows - matched_tally_count

    return jsonify({
        'success': True,
        'inserted': inserted_count,
        'msg': f'{inserted_count} records reconciled and saved to bft_matched.',
        'matched_count': matched_bank_count,
        'unmatched_bf_count': unmatched_bf_count,
        'unmatched_tally_count': unmatched_tally_count
    })
