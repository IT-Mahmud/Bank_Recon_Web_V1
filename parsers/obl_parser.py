# obl_parser.py

import pandas as pd

def generate_uid(rownum, date_val, balance_val):
    bank_code = "OBL"
    rownum_str = f"{rownum:03d}"
    try:
        ymd = pd.to_datetime(str(date_val)).strftime("%Y%m%d")
        hex_date = hex(int(ymd))[2:] if pd.notnull(date_val) else "0"
    except Exception:
        hex_date = "0"
    try:
        bal_int = int(round(float(str(balance_val).replace(",", ""))))
        hex_balance = hex(bal_int)[2:] if pd.notnull(balance_val) else "0"
    except Exception:
        hex_balance = "0"
    return f"{bank_code}_{rownum_str}_{hex_date}_{hex_balance}"

def parse_obl_statement(file_path):
    df_raw = pd.read_excel(file_path, dtype=str, header=None)
    target_headers = ["Tran Date", "Tran Type", "Reference No",
                      "Value Date", "Debit", "Credit", "Balance"]
    header_row_idx = None
    for idx, row in df_raw.iterrows():
        row_vals = [str(x).strip().lower() for x in row.tolist()]
        if all(h.lower() in row_vals for h in target_headers):
            header_row_idx = idx
            break
    if header_row_idx is None:
        raise ValueError("Header row with required columns not found.")

    # Metadata (not required for DB)
    meta_values = {}
    meta_values["Account Number"] = str(df_raw.iloc[6, 12])
    meta_values["Account Number"] = meta_values["Account Number"].replace("A/C No:", "").strip()

    # Transaction data
    data_df = pd.read_excel(file_path, dtype=str, header=header_row_idx)
    data_df.columns = [col.strip() for col in data_df.columns]
    data_df = data_df[[col for col in target_headers if col in data_df.columns]]
    data_df = data_df.dropna(how='all')
    data_df = data_df[~(data_df.replace('', pd.NA).isna().all(axis=1))].reset_index(drop=True)

    # Date normalization
    if "Tran Date" in data_df.columns:
        data_df["norm_obl_date"] = pd.to_datetime(
            data_df["Tran Date"], format="%d-%m-%Y", errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        data_df.drop(columns=["Tran Date"], inplace=True)
        cols = ["norm_obl_date"] + [c for c in data_df.columns if c != "norm_obl_date"]
        data_df = data_df[cols]

    # Remove unwanted rows
    def extract_and_remove(pattern):
        mask = data_df.apply(
            lambda row: row.astype(str).str.contains(pattern, case=False, regex=True).any(), axis=1
        )
        return data_df[~mask]
    data_df = extract_and_remove(r"Balance Brought Forward")
    data_df = extract_and_remove(r"NEW BALANCE")
    pattern_excl = r"^\d+\s*(CREDIT|DEBIT)\(S\)$"
    mask_excl = data_df.apply(
        lambda row: row.astype(str).str.match(pattern_excl, case=False, na=False).any(), axis=1
    )
    data_df = data_df[~mask_excl].reset_index(drop=True)

    # Numeric columns
    for col in ["Debit", "Credit", "Balance"]:
        if col in data_df.columns:
            data_df[col] = (
                data_df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace("", "0")
                .astype(float)
                .round(2)
            )

    # UID
    uid_list = []
    balance_col = "Balance"
    date_col = "norm_obl_date"
    for idx, row in data_df.iterrows():
        uid = generate_uid(idx + 1, row.get(date_col, ""), row.get(balance_col, ""))
        uid_list.append(uid)
    data_df.insert(0, "obl_uid", uid_list)

    # Placeholder for vendor extraction (if needed later)
    data_df["der_obl_ven"] = ""

    # Add account number column
    data_df["obl_acct_no"] = meta_values.get("Account Number", "UnknownAcc")

    return data_df
