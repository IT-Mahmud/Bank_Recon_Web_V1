# bank_tally_match_logic_mtb.py

import re

# --- Config for MTB bank extraction ---
BANK_CONFIG = {
    "narration_column": "Transaction Detail",
    "withdrawal_column": "Withdrawal (Dr.)",
    "deposit_column": "Deposit (Cr.)",
    "prefixes": [
        {"prefix": "LC ISSUE CHARGE :", "min_digits": 5},
        {
            "dynamic_prefix": "number to number",
            "extract_after_nth_number": 2,
            "min_digits": 5
        },
        {
            "dynamic_prefix": "USD",
            "extract_after_nth_number": 1,
            "min_digits": 5
        },
        {
            "dynamic_prefix": "ACCEPTANCE COMM",
            "extract_after_nth_slash": 3,
            "min_digits": 5
        }
    ]
}

def extract_cheque_ref(text, rule):
    text = str(text)
    if "extract_after_nth_slash" in rule:
        n = rule["extract_after_nth_slash"]
        parts = [s for s in text.split("/") if s.strip()]
        if len(parts) > n:
            text = parts[n]
        else:
            return None
    min_digits = rule.get("min_digits", 5)
    numbers = re.findall(rf"[\d,]{{{min_digits},}}", text)
    nth = rule.get("extract_after_nth_number", 1)
    if len(numbers) >= nth:
        return re.sub(r'[,\s\-]', '', numbers[nth - 1])
    return None

def get_first_cheque_ref(text, prefixes):
    for p in prefixes:
        if "prefix" in p:
            prefix = p["prefix"]
            min_digits = p["min_digits"]
            pattern = rf"{re.escape(prefix)}([\d\- ]{{{min_digits},}})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return re.sub(r'[\-\s]', '', match.group(1))
        elif "dynamic_prefix" in p:
            result = extract_cheque_ref(text, p)
            if result:
                return result
    return None

def extract_bank_cheque_ref(text):
    return get_first_cheque_ref(text, BANK_CONFIG['prefixes'])

# --- Config for Tally extraction ---
TALLY_CONFIG = {
    "narration_column": "Particulars",
    "debit_column": "Debit",
    "credit_column": "Credit",
    "prefixes": [
        {"prefix": "$", "min_digits": 5},
        {"prefix": "cq-", "min_digits": 5},
        {"prefix": "A/C-", "min_digits": 5},
        {"prefix": "CD-", "min_digits": 5},
        {"prefix": "STD-", "min_digits": 5},
        {"prefix": "OD#", "min_digits": 5},
        {"prefix": "CQ-", "min_digits": 5},
        {"prefix": "(Hypo)-", "min_digits": 5},
        {"prefix": "GULC#", "min_digits": 5}
    ]
}

def extract_tally_cheque_ref(text):
    return get_first_cheque_ref(text, TALLY_CONFIG['prefixes'])

def normalize_ref(ref):
    return ref.lstrip('0') if isinstance(ref, str) else ref

def match_cheques(bank_df, tally_df, start_id=1):
    """
    MTB cheque matching: only unmatched (is_matched == 0) rows.
    Returns bt_matched table as a list of dicts.
    """
    # Filter for unmatched only
    bank_df = bank_df[bank_df['is_matched'] == 0].copy()
    tally_df = tally_df[tally_df['is_matched'] == 0].copy()

    bank_df['cheque_ref'] = bank_df[BANK_CONFIG['narration_column']].apply(extract_bank_cheque_ref).apply(normalize_ref)
    tally_df['cheque_ref'] = tally_df[TALLY_CONFIG['narration_column']].apply(extract_tally_cheque_ref).apply(normalize_ref)

    matched = []
    used_bank = set()
    used_tally = set()
    match_id = start_id

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

    return matched
