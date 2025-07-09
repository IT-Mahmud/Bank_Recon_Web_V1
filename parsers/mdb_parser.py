# mdb_parser.py

import pandas as pd
import re
from calendar import month_name

MDB_ACCOUNT_NUMBERS = {
    "0011-1050011026",
    "0011-1060000331",
    # Add all valid Midland Bank account numbers here
}


def parse_mdb_statement(input_file):
    header_cols = ["Date", "Particular", "Withdrawal", "Deposit", "Balance"]
    df_all = pd.read_excel(input_file, header=None, dtype=str)

    # Find header row
    header_row_idx = None
    for idx, row in df_all.iterrows():
        vals = [str(x).strip().lower() for x in row.tolist()]
        if all(col.lower() in vals for col in header_cols):
            header_row_idx = idx
            break
    if header_row_idx is None:
        raise Exception("Header row with expected columns not found.")

    # Get metadata (everything above header row)
    metadata_raw = df_all.iloc[:header_row_idx]
    # Extract account number from row 3, col 11 (iloc[2, 11])
    try:
        account_number_raw = str(metadata_raw.iloc[2, 11])
        account_number = account_number_raw.replace(":", "").strip()
        m = re.search(r'([0-9\-]+)', account_number)
        if m:
            account_number = m.group(1)
        if not account_number:
            account_number = "UnknownAcc"
    except Exception:
        account_number = "UnknownAcc"

    if account_number not in MDB_ACCOUNT_NUMBERS:
        raise ValueError(
            f"Account {account_number} is not listed for Midland Bank. "
            "Please make sure you're uploading the correct statement."
        )

    # Statement period extraction
    try:
        statement_period_cell = str(metadata_raw.iloc[6, 0])
    except Exception:
        raise Exception(
            "Could not access metadata cell [6, 0] for statement period.")

    if not statement_period_cell.strip().startswith("Statement Period:"):
        raise Exception(
            "Statement period cell missing or misformatted in [6, 0].")

    # Extract date strings from the format "Statement Period: 01-Feb-2025 To 28-Feb-2025"
    match = re.search(
        r'Statement Period:\s*([\d\-A-Za-z]+)\s*To\s*([\d\-A-Za-z]+)', statement_period_cell)
    if not match:
        raise Exception("Could not parse dates in statement period cell.")

    first_date_str, last_date_str = match.group(1), match.group(2)
    try:
        first_date = pd.to_datetime(first_date_str, format="%d-%b-%Y")
        last_date = pd.to_datetime(last_date_str, format="%d-%b-%Y")
    except Exception:
        raise Exception("Date format error in statement period cell.")

    # Extract month and year
    statement_month = ""
    statement_year = ""
    if first_date.month == last_date.month:
        statement_month = month_name[first_date.month]
    if first_date.year == last_date.year:
        statement_year = str(first_date.year)

    # Parse and clean transaction data
    df_data = pd.read_excel(input_file, header=header_row_idx, dtype=str)
    df_data = df_data[header_cols]
    df_data = df_data.dropna(how='all')

    if "Date" in df_data:
        df_data["Date"] = pd.to_datetime(
            df_data["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    def is_duplicate_header(row):
        date_val = str(row["Date"]).strip().lower()
        if date_val not in ["", "nan", "nat"]:
            return False
        return sum(str(row[c]).strip().lower() == c.lower() for c in header_cols[1:]) >= 2

    df_data = df_data[~df_data.apply(
        is_duplicate_header, axis=1)].reset_index(drop=True)
    for col in header_cols:
        df_data = df_data[df_data[col].str.lower() != col.lower()]
    df_data = df_data.dropna(how="all").reset_index(drop=True)
    df_data = df_data[~df_data.apply(lambda row: all(
        str(x).strip() == "" for x in row), axis=1)].reset_index(drop=True)
    df_data = df_data[df_data["Particular"].str.strip(
    ).str.lower() != "balance b/f"].reset_index(drop=True)

    # Normalize numeric columns
    for col in ["Withdrawal", "Deposit", "Balance"]:
        df_data[col] = df_data[col].replace({',': ''}, regex=True)
        df_data[col] = df_data[col].apply(
            lambda x: str(x).strip() if pd.notna(x) else "")
        df_data[col] = pd.to_numeric(df_data[col], errors="coerce").round(2)

    # Vendor extraction
    def normalize_vendor_name(name):
        s = str(name)
        s = s.strip()
        s = re.sub(r'^M[\s./\\-]*S[\s./\\-]*', '', s, flags=re.IGNORECASE)
        s = s.replace(".", "").replace(" ", "").replace("-", "")
        return s.upper()

    def extract_bank_ven(row):
        p = str(row["Particular"]).strip()

        def get_between_slashes(text, end_from_right):
            slashes = [m.start() for m in re.finditer("/", text)]
            if len(slashes) < (end_from_right + 1):
                return ""
            start = slashes[0] + 1
            end = slashes[-end_from_right]
            return text[start:end].strip()
        if p.lower().startswith("rtgs rtgs outward"):
            vendor_raw = get_between_slashes(p, 6)
            return normalize_vendor_name(vendor_raw)
        if p.lower().startswith("rtgs rtgs inward"):
            vendor_raw = get_between_slashes(p, 5)
            return normalize_vendor_name(vendor_raw)
        if p.lower().startswith("charge rtgs charge"):
            vendor_raw = get_between_slashes(p, 6)
            return normalize_vendor_name(vendor_raw)
        if p.lower().startswith("clg hv"):
            vendor_raw = get_between_slashes(p, 4)
            return normalize_vendor_name(vendor_raw)
        sl = [m.start() for m in re.finditer("/", p)]
        if p.lower().startswith("transfer beftn outward") and len(sl) >= 4:
            start = sl[2] + 1
            end = sl[3]
            vendor_raw = p[start:end].strip()
            return normalize_vendor_name(vendor_raw)
        if re.match(r'^CLG- InwardCA\d{7} RV', p, re.IGNORECASE):
            idx = p.lower().find("pay to :")
            if idx != -1:
                after_payto = p[idx + len("pay to :"):].strip()
                vendor_part = after_payto.split("/")[0].strip()
                return normalize_vendor_name(vendor_part)
        if p.lower().startswith("on-line cashca"):
            match = re.match(r'on-line cashca(\d{7})', p, re.IGNORECASE)
            if match:
                end_digits = match.end()
                next_slash = p.find("/", end_digits)
                if next_slash != -1:
                    vendor_portion = p[end_digits:next_slash].strip()
                else:
                    vendor_portion = p[end_digits:].strip()
                for drop_phrase in ["Number of Tran. exceeded TP.", "No. of Tran. exceeded TP."]:
                    vendor_portion = vendor_portion.split(drop_phrase)[
                        0].strip()
                return normalize_vendor_name(vendor_portion)
        elif p.lower().startswith("on-line cash"):
            remainder = p[len("On-Line Cash"):].strip()
            if "/" in remainder:
                vendor_part = remainder.split("/")[0].strip()
                return normalize_vendor_name(remainder)
            else:
                return normalize_vendor_name(remainder)
        return ""

    df_data["bank_ven"] = df_data.apply(extract_bank_ven, axis=1)

    # UID logic
    def to_hex_date(date_str):
        try:
            dt = pd.to_datetime(date_str, errors="coerce")
            if pd.isna(dt):
                return "0"
            ymd = dt.strftime("%Y%m%d")
            return format(int(ymd), "x")
        except Exception:
            return "0"

    def to_hex_balance(balance):
        try:
            bal = float(balance)
            bal_int = int(round(bal))
            return format(bal_int, "x")
        except Exception:
            return "0"

    uid_list = []
    for idx, row in df_data.iterrows():
        row_num = str(idx + 1).zfill(6)
        hex_date = to_hex_date(row.get("Date", ""))
        hex_balance = to_hex_balance(row.get("Balance", 0))
        uid = f"B_MDB_{hex_date}_{hex_balance}_{row_num}"
        uid_list.append(uid)
    df_data.insert(0, "bank_uid", uid_list)

    # Insert account number statement_month and statement_year columns
    df_data["acct_no"] = account_number
    df_data["statement_month"] = statement_month
    df_data["statement_year"] = statement_year

    # Add the 'bank_code' column (MDB for Midland Bank)
    df_data['bank_code'] = 'MDB'  # You can change this if needed

    # Rename columns
    df_data = df_data.rename(columns={
        "Date": "B_Date",
        "Particular": "B_Particulars",
        "Withdrawal": "B_Withdrawal",
        "Deposit": "B_Deposit",
        "Balance": "B_Balance"
    })

    return df_data
