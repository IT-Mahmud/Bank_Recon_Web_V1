# logics/bank_fin_match_logic.py

import pandas as pd
from itertools import combinations

MAX_FINANCE_COMBO = 10  # Match 10 finance payment records against 1  bank transaction record

# Bank-specific vendor alias dictionaries: Map inexact bank and finance vendor names (e.g., "ABC & Co." to "ABC and Co.").
vendor_alias_dicts = {
    "MDB": {
        "JOYNALANDSONS": "JOYNALSONS",
        "TALIANDCO": "TALICO",
    },
    "MTB": {
        "BANKVENDOR": "FINVENDORALIAS",
    },
}

def get_vendor_alias(val, bank_type):
    bank_alias_dict = vendor_alias_dicts.get(bank_type, {})
    return bank_alias_dict.get(str(val).strip().upper(), str(val).strip().upper())

def is_weekend_match(bank_date, fin_date):
    try:
        bd = pd.to_datetime(bank_date)
        fd = pd.to_datetime(fin_date)
        return bd.strftime('%A') == 'Sunday' and fd.strftime('%A') == 'Thursday'
    except:
        return False

def normalize_for_match(df, vendor_col, amt_col, date_col, bank_type=None):
    df = df.copy()  # <--- Add this line at the top to avoid modifying the original DataFrame
    df['_vendor_first5'] = df[vendor_col].str.upper().str.strip().str[:5]
    if bank_type is not None:
        df['_ven_alias'] = df[vendor_col].apply(
            lambda v: get_vendor_alias(v, bank_type))
    else:
        df['_ven_alias'] = df[vendor_col].str.upper().str.strip()
    df['_norm_amt'] = pd.to_numeric(df[amt_col], errors='coerce').round(2)
    df['_norm_date'] = df[date_col]
    return df

def bank_fin_match(bank_df, finance_df, config, bank_type, account_number=None, max_combo=MAX_FINANCE_COMBO):
    # Filter finance_df by Sender Bank if the column exists
    if 'F_Sender_Bank' in finance_df.columns:
        finance_df = finance_df[finance_df['F_Sender_Bank'] == bank_type]
    # Filter finance_df by Sender Account if the column exists and account_number is provided
    if account_number and 'F_Sender_Account' in finance_df.columns:
        finance_df = finance_df[finance_df['F_Sender_Account'] == account_number]
    bank_amt_col = config['debit_col']
    bank_date_col = config['date_col']
    bank_vendor_col = config['bank_ven_col']
    fin_amt_col = 'F_Credit_Amount' if 'F_Credit_Amount' in finance_df.columns else 'Amount'
    fin_date_col = 'F_Payment_Date' if 'F_Payment_Date' in finance_df.columns else 'Date'
    fin_vendor_col = 'fin_ven' if 'fin_ven' in finance_df.columns else 'Vendor'
    bank_df = normalize_for_match(
        bank_df, bank_vendor_col, bank_amt_col, bank_date_col, bank_type)
    finance_df = normalize_for_match(
        finance_df, fin_vendor_col, fin_amt_col, fin_date_col, None)

    matched_rows = []
    unmatched_bank_idxs = []
    unmatched_finance_idxs = set(finance_df.index)
    match_id_counter = 1

    # 1-to-1 direct match loop
    for b_idx, b_row in bank_df.iterrows():
        match_found = False
        for f_idx, f_row in finance_df.iterrows():
            if f_idx not in unmatched_finance_idxs:
                continue
            is_weekend = is_weekend_match(
                b_row[bank_date_col], f_row[fin_date_col])
            if (
                b_row['_vendor_first5'] == f_row['_vendor_first5']
                and b_row['_norm_amt'] == f_row['_norm_amt']
                and (b_row['_norm_date'] == f_row['_norm_date'] or is_weekend)
            ):
                bf_match_id = f"{match_id_counter:04}"
                matched_rows.append({
                    'bf_match_id': bf_match_id, 'source': 'Bank', 'match_type': '1 to 1',
                    **b_row.drop([c for c in b_row.index if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                })
                matched_rows.append({
                    'bf_match_id': bf_match_id, 'source': 'Finance', 'match_type': '1 to 1',
                    **f_row.drop([c for c in f_row.index if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                })
                unmatched_finance_idxs.remove(f_idx)
                match_id_counter += 1
                match_found = True
                break
        if not match_found:
            unmatched_bank_idxs.append(b_idx)

    # 1-to-N direct sum matching loop
    unmatched_bank_idxs_1ton = []
    for b_idx in unmatched_bank_idxs:
        b_row = bank_df.loc[b_idx]
        candidates = [
            f_idx for f_idx in unmatched_finance_idxs
            if (b_row['_vendor_first5'] == finance_df.loc[f_idx, '_vendor_first5'] and
                (b_row['_norm_date'] == finance_df.loc[f_idx, '_norm_date'] or
                 is_weekend_match(b_row[bank_date_col], finance_df.loc[f_idx, fin_date_col])))
        ]
        found_combo = False
        for r in range(2, max_combo + 1):
            for combo in combinations(candidates, r):
                amt_sum = sum([finance_df.loc[f_idx, '_norm_amt']
                              for f_idx in combo])
                if pd.isna(amt_sum) or pd.isna(b_row['_norm_amt']):
                    continue
                if round(amt_sum, 2) == round(b_row['_norm_amt'], 2):
                    bf_match_id = f"{match_id_counter:04}"
                    matched_rows.append({
                        'bf_match_id': bf_match_id, 'source': 'Bank', 'match_type': f'1 to {r}',
                        **b_row.drop([c for c in b_row.index if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                    })
                    for f_idx in combo:
                        matched_rows.append({
                            'bf_match_id': bf_match_id, 'source': 'Finance', 'match_type': f'1 to {r}',
                            **finance_df.loc[f_idx].drop([c for c in finance_df.columns if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                        })
                        unmatched_finance_idxs.remove(f_idx)
                    match_id_counter += 1
                    found_combo = True
                    break
            if found_combo:
                break
        if not found_combo:
            unmatched_bank_idxs_1ton.append(b_idx)

    # 1-to-1 vendor alias matching loop
    still_unmatched_bank_idxs = []
    for b_idx in unmatched_bank_idxs_1ton:
        b_row = bank_df.loc[b_idx]
        match_found = False
        for f_idx in list(unmatched_finance_idxs):
            f_row = finance_df.loc[f_idx]
            is_weekend = is_weekend_match(
                b_row[bank_date_col], f_row[fin_date_col])
            if (
                b_row['_ven_alias'] == f_row['_ven_alias']
                and b_row['_norm_amt'] == f_row['_norm_amt']
                and (b_row['_norm_date'] == f_row['_norm_date'] or is_weekend)
            ):
                bf_match_id = f"{match_id_counter:04}"
                matched_rows.append({
                    'bf_match_id': bf_match_id, 'source': 'Bank', 'match_type': '1 to 1 (alias)',
                    **b_row.drop([c for c in b_row.index if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                })
                matched_rows.append({
                    'bf_match_id': bf_match_id, 'source': 'Finance', 'match_type': '1 to 1 (alias)',
                    **f_row.drop([c for c in f_row.index if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                })
                unmatched_finance_idxs.remove(f_idx)
                match_id_counter += 1
                match_found = True
                break
        if not match_found:
            still_unmatched_bank_idxs.append(b_idx)

    # 1-to-N vendor alias sum matching loop
    unmatched_bank_idxs_alias_1ton = []
    for b_idx in still_unmatched_bank_idxs:
        b_row = bank_df.loc[b_idx]
        candidates = [
            f_idx for f_idx in unmatched_finance_idxs
            if (b_row['_ven_alias'] == finance_df.loc[f_idx, '_ven_alias'] and
                (b_row['_norm_date'] == finance_df.loc[f_idx, '_norm_date'] or
                 is_weekend_match(b_row[bank_date_col], finance_df.loc[f_idx, fin_date_col])))
        ]
        found_combo = False
        for r in range(2, max_combo + 1):
            for combo in combinations(candidates, r):
                amt_sum = sum([finance_df.loc[f_idx, '_norm_amt']
                              for f_idx in combo])
                if pd.isna(amt_sum) or pd.isna(b_row['_norm_amt']):
                    continue
                if round(amt_sum, 2) == round(b_row['_norm_amt'], 2):
                    bf_match_id = f"{match_id_counter:04}"
                    matched_rows.append({
                        'bf_match_id': bf_match_id, 'source': 'Bank', 'match_type': f'1 to {r} (alias)',
                        **b_row.drop([c for c in b_row.index if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                    })
                    for f_idx in combo:
                        matched_rows.append({
                            'bf_match_id': bf_match_id, 'source': 'Finance', 'match_type': f'1 to {r} (alias)',
                            **finance_df.loc[f_idx].drop([c for c in finance_df.columns if c.startswith('_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
                        })
                        unmatched_finance_idxs.remove(f_idx)
                    match_id_counter += 1
                    found_combo = True
                    break
            if found_combo:
                break
        if not found_combo:
            unmatched_bank_idxs_alias_1ton.append(b_idx)

    unmatched_bank = [
        bank_df.loc[idx].drop([c for c in bank_df.columns if c.startswith(
            '_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
        for idx in unmatched_bank_idxs_alias_1ton
    ]
    unmatched_finance = [
        finance_df.loc[idx].drop([c for c in finance_df.columns if c.startswith(
            '_vendor_') or c.startswith('_ven_alias') or c.startswith('_norm_')]).to_dict()
        for idx in unmatched_finance_idxs
    ]
    return matched_rows, unmatched_bank, unmatched_finance

def flatten_bf_matches(matched_rows, bank_cols, fin_cols, run_tag=""):
    records = []
    match_id_map = {}
    next_counter = 1
    for row in matched_rows:
        orig = row.get("bf_match_id")
        if orig not in match_id_map:
            match_id_map[orig] = next_counter
            next_counter += 1
        row_match_id = f"BFM_{run_tag}_{match_id_map[orig]:04}" if run_tag else orig
        record = {
            "bf_match_id": row_match_id,
            "bf_source": row.get("source"),
            "bf_match_type": row.get("match_type", ""),
        }
        # if row["source"] == "Bank":
        #     for col in bank_cols:
        #         if col == "id":
        #             record["bank_id"] = row.get(col, "")
        #         else:
        #             record[col] = row.get(col, "")
        # elif row["source"] == "Finance":
        #     for col in fin_cols:
        #         if col == "id":
        #             record["fin_id"] = row.get(col, "")
        #         else:
        #             record[col] = row.get(col, "")
        if row["source"] == "Bank":
            for col in bank_cols:
                record[col] = row.get(col, "")
        elif row["source"] == "Finance":
            for col in fin_cols:
                record[col] = row.get(col, "")
        
        records.append(record)
    return pd.DataFrame(records)
