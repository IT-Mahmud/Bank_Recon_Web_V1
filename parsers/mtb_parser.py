# mtb_parser.py

import pandas as pd
import re
from calendar import month_name

MTB_ACCOUNT_NUMBERS = {
    "0020320004355",  # add more MTB account numbers if needed
}

# --- Helper Function 1: Extract Bank Vendor ---
def extract_bank_vendor(detail):
    """
    Extracts the vendor name from the 'Transaction Detail' column.
    Removes unnecessary characters and standardizes the format.
    """
    if not isinstance(detail, str):
        return ""
    text = ' '.join(detail.split()).strip()
    vendor = ""
    
    if text.startswith("RTGS/MTB"):
        parts = text.split('/')
        if len(parts) >= 3:
            vendor = ' '.join(parts[2:-1]).strip()
    elif text.startswith("EFT OCE"):
        parts = [p.strip() for p in text.split('/') if p.strip()]
        if len(parts) >= 4:
            vendor = parts[3]
    
    # Clean unwanted patterns and spaces
    vendor = re.sub(r"\bM[\.\s/\\]*S\b", "", vendor, flags=re.IGNORECASE)
    vendor = vendor.replace(".", "").replace(" ", "")
    
    return vendor.upper().strip()

# --- Helper Function 2: Convert Date to Hex ---
def to_hex_date(date_str):
    """
    Converts a date string into a hexadecimal format (YYYYMMDD -> hex).
    """
    try:
        dt = pd.to_datetime(date_str, errors="coerce")
        if pd.isna(dt):
            return "0"
        ymd = dt.strftime("%Y%m%d")
        return format(int(ymd), "x")
    except Exception:
        return "0"

# --- Helper Function 3: Convert Balance to Hex ---
def to_hex_balance(balance):
    """
    Converts a numeric balance into a hexadecimal format.
    """
    try:
        bal = float(balance)
        bal_int = int(round(bal))
        return format(bal_int, "x")
    except Exception:
        return "0"

# --- Helper Function 4: Extract Account Number ---
def extract_account_number(metadata):
    """
    Extracts the account number from the metadata.
    """
    try:
        account_number_raw = str(metadata.iloc[17, 5])
        account_number = account_number_raw.strip()
        account_number = account_number.lstrip("'")  # <-- REMOVE LEADING QUOTE

    except Exception:
        account_number = "UnknownAcc"
    
    if not account_number or account_number == "nan":
        account_number = "UnknownAcc"
    
    return account_number

# --- Helper Function 5: Extract Statement Period ---
def extract_statement_period(metadata):
    """
    Extracts the statement period from the metadata.
    """
    try:
        statement_period_cell = str(metadata.iloc[29, 5])
    except Exception:
        raise Exception("Could not access metadata cell [29, 5] for statement period.")
    
    if not statement_period_cell or "To" not in statement_period_cell:
        raise Exception("Statement period cell missing or misformatted in [29, 5].")

    match = re.search(r'([\d]{2}-[\d]{2}-[\d]{4})\s*To\s*([\d]{2}-[\d]{2}-[\d]{4})', statement_period_cell)
    if not match:
        raise Exception("Could not parse dates in statement period cell.")
    
    first_date_str, last_date_str = match.group(1), match.group(2)
    
    try:
        first_date = pd.to_datetime(first_date_str, format="%d-%m-%Y")
        last_date = pd.to_datetime(last_date_str, format="%d-%m-%Y")
    except Exception:
        raise Exception("Date format error in statement period cell.")
    
    return first_date, last_date

# --- Main Parsing Function ---
def parse_mtb_statement(file_path, sheet_name="AcStatementReport"):
    """
    Main function to parse the MTB statement and clean the data.
    """
    # Read the Excel file (all sheets)
    if file_path.lower().endswith(".xlsx"):
        df = pd.read_excel(file_path, sheet_name=None, dtype=str)
    else:
        df = pd.read_excel(file_path, sheet_name=None,
                           dtype=str, engine="xlrd")
    
    # Find the relevant sheet
    if sheet_name not in df:
        raise ValueError(f"Sheet '{sheet_name}' not found.")
    df_raw = df[sheet_name]

    # Find header row (where required headers are found)
    headers_required = [
        "Date", "Transaction Detail", "Ref/Cheque No", "Withdrawal (Dr.)",
        "Deposit (Cr.)", "Balance", "Branch"
    ]
    header_row_index = None
    for i, row in df_raw.iterrows():
        row_clean = row.fillna("").astype(str).str.strip().tolist()
        if all(col in row_clean for col in headers_required):
            header_row_index = i
            break
    if header_row_index is None:
        raise ValueError("Required headers not found.")

    # Get metadata and main data
    metadata = df_raw.iloc[:header_row_index]
    df_clean = df_raw.iloc[header_row_index:].copy()
    df_clean.columns = df_clean.iloc[0].astype(str).str.strip()
    df_clean = df_clean[1:].reset_index(drop=True)
    df_clean = df_clean[headers_required]

    # Clean data (strip spaces, replace NaN with empty string)
    df_clean = df_clean.applymap(lambda x: str(x).strip() if pd.notna(x) else "")

    # Clean and format the "Date" column
    if "Date" in df_clean.columns:
        df_clean["Date"] = pd.to_datetime(
            df_clean["Date"], format="%d-%m-%Y", errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    # Clean numeric columns: "Withdrawal", "Deposit", "Balance"
    amt_cols = ["Withdrawal (Dr.)", "Deposit (Cr.)", "Balance"]
    for col in amt_cols:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].str.replace(r"(?<=\d),(?=\d)", "", regex=True)
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").round(2)

    # Extract vendor information from "Transaction Detail"
    df_clean["bank_ven"] = df_clean["Transaction Detail"].apply(lambda x: extract_bank_vendor(x))

    # Generate unique IDs based on the transaction row and balance
    uid_prefix = "B_MTB"
    uid_list = []
    for idx, row in df_clean.iterrows():
        row_num = str(idx + 1).zfill(6)
        hex_date = to_hex_date(row.get("Date", ""))
        hex_balance = to_hex_balance(row.get("Balance", 0))
        uid = f"{uid_prefix}_{hex_date}_{hex_balance}_{row_num}"
        uid_list.append(uid)
    df_clean.insert(0, "bank_uid", uid_list)

    # Extract account number from metadata
    account_number = extract_account_number(metadata)
    df_clean["acct_no"] = account_number

    if account_number not in MTB_ACCOUNT_NUMBERS:
        raise ValueError(
            f"Account number {account_number} not allowed for Mutual Trust Bank. "
            "Please check your upload or select the correct bank."
        )

    # Extract statement period (start and end dates)
    first_date, last_date = extract_statement_period(metadata)
    
    statement_month = ""
    statement_year = ""
    if first_date.month == last_date.month:
        statement_month = month_name[first_date.month]
    if first_date.year == last_date.year:
        statement_year = str(first_date.year)

    df_clean["statement_month"] = statement_month
    df_clean["statement_year"] = statement_year

    # Rename columns before returning the dataframe
    df_clean = df_clean.rename(columns={
        "Date": "B_Date",
        "Transaction Detail": "B_Particulars",
        "Withdrawal (Dr.)": "B_Withdrawal",
        "Deposit (Cr.)": "B_Deposit",
        "Balance": "B_Balance",
        "Ref/Cheque No": "B_Ref_Cheque",
    })

    # Drop the "Branch" column before saving
    df_clean = df_clean.drop('Branch', axis=1)
    
    # Add the 'bank_code' column (MTB for Mutual Trust Bank)
    df_clean['bank_code'] = 'MTB'  # You can change this if needed

    
    return df_clean
