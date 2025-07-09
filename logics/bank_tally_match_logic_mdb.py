# bank_tally_match_logic_mdb.py

import re

# --- Config for MDB bank extraction ---
BANK_CONFIG = {
    "narration_column": "B_Particulars",
    "withdrawal_column": "B_Withdrawal",
    "deposit_column": "B_Deposit",
    "prefixes": [
        {"prefix": "on-line cashca", "min_digits": 5},
        {"prefix": "clg- inwardca", "min_digits": 5},
        {"dynamic_prefix": "RTGS RTGS Outward",
         "extract_between_nth_and_mth_slash": [2, 3], "min_digits": 5},
        {"dynamic_prefix": "RTGS RTGS INWARD",
         "extract_between_nth_and_mth_slash": [2, 3], "min_digits": 5},
        {"dynamic_prefix": "CLG HV",
         "extract_between_nth_and_mth_slash": [3, 4], "min_digits": 5}
    ]
}

def extract_bank_cheque_ref(text):
    text = str(text)
    for p in BANK_CONFIG['prefixes']:
        if "prefix" in p:
            pattern = rf"{re.escape(p['prefix'])}([\d\- ]{{{p['min_digits']},}})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return re.sub(r'[\s,-]', '', match.group(1))
        elif "dynamic_prefix" in p:
            if text.lower().startswith(p["dynamic_prefix"].lower()):
                n, m = p["extract_between_nth_and_mth_slash"]
                parts = [seg for seg in text.split("/") if seg.strip()]
                if len(parts) > n:
                    candidate = parts[n]
                    value = re.sub(r'[\s,-]', '', candidate)
                    if len(value) >= p['min_digits']:
                        return value
    return None

# --- Config for Tally extraction ---
TALLY_CONFIG = {
    "narration_column": "T_Particulars",
    "debit_column": "T_Debit",
    "credit_column": "T_Credit",
    "prefixes": [
        {"prefix": "cq-", "min_digits": 5},
        {"prefix": "Cheque No : C ", "min_digits": 5},
        {"prefix": "A/C-", "min_digits": 5},
        {"prefix": "CD-", "min_digits": 5},
        {"prefix": "STD-", "min_digits": 5},
        {"prefix": "OD#", "min_digits": 5},
        {"prefix": "CQ-", "min_digits": 5},
        {"prefix": "(Hypo)-", "min_digits": 5},
        {"prefix": "SND-", "min_digits": 5}
    ]
}

def extract_tally_cheque_ref(text):
    text = str(text)
    for p in TALLY_CONFIG['prefixes']:
        pattern = rf"{re.escape(p['prefix'])}([\d\- ]{{{p['min_digits']},}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return re.sub(r'[\-\s]', '', match.group(1))
    return None

def match_cheques(bank_df, tally_df, start_id=1):
    # Filter for unmatched only
    # bank_df = bank_df[bank_df['is_matched'] == 0].copy()
    # tally_df = tally_df[tally_df['is_matched'] == 0].copy()


    bank_df = bank_df[bank_df['bf_is_matched'] == 0].copy()
    tally_df = tally_df[tally_df['bft_is_matched'] == 0].copy()


    bank_df['cheque_ref'] = bank_df[BANK_CONFIG['narration_column']].apply(extract_bank_cheque_ref)
    tally_df['cheque_ref'] = tally_df[TALLY_CONFIG['narration_column']].apply(extract_tally_cheque_ref)

    matched = []
    used_bank = set()
    used_tally = set()
    match_id = start_id

    # Build map for quick lookup
    tally_cheque_map = {}
    for idx, row in tally_df.iterrows():
        ref = row['cheque_ref']
        if ref:
            tally_cheque_map.setdefault(ref, []).append(idx)

    for i, b_row in bank_df.iterrows():
        ref = b_row['cheque_ref']
        if not ref or i in used_bank:
            continue
        withdrawal = float(b_row.get(BANK_CONFIG['withdrawal_column'], 0) or 0)
        deposit = float(b_row.get(BANK_CONFIG['deposit_column'], 0) or 0)
        for j in tally_cheque_map.get(ref, []):
            if j in used_tally:
                continue
            t_row = tally_df.loc[j]
            tally_credit = float(t_row.get(TALLY_CONFIG['credit_column'], 0) or 0)
            tally_debit = float(t_row.get(TALLY_CONFIG['debit_column'], 0) or 0)
            if (withdrawal and withdrawal == tally_credit) or (deposit and deposit == tally_debit):
                match_id_str = f"BTM_{match_id:04d}"
                matched.append({**b_row.to_dict(), 'bt_match_id': match_id_str, 'bt_source': 'Bank'})
                matched.append({**t_row.to_dict(), 'bt_match_id': match_id_str, 'bt_source': 'Tally'})
                used_bank.add(i)
                used_tally.add(j)
                match_id += 1
                break

    # Return only matched pairs (bt_matched table)
    return matched
