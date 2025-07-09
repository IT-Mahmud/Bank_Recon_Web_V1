import pandas as pd
import re
import string


def derive_vendor(name):
    if not isinstance(name, str):
        return ""
    name = name.upper().strip()
    name = re.sub(r"^(M[\s\.\/]*S[\s\.]*)", "", name)
    name = re.sub(rf"[{re.escape(string.punctuation)}]", "", name)
    name = name.replace(" ", "")
    return name


def parse_fin_statement(input_file, sheet_name=None, payment_month=None):
    expected_header = [
        "Routing No", "Receiving A/C No", "Credit Amount", "Receiver Name",
        "Bank Name", "Branch Name", "Sender Name", "Sender Account", "Sender Bank",
        "Unit Name", "Team Name", "New Project", "Project", "Sub Project", "PO",
        "Status", "Voucher Date", "Voucher No", "Payment Date", "Payment Month",
        "Remarks", "Mark", "Concern"
    ]

    with pd.ExcelFile(input_file) as xl:
        if sheet_name is None:
            sheet_name = xl.sheet_names[0]

        df_all = xl.parse(sheet_name, header=None, dtype=str)

        header_row_idx = None
        for idx, row in df_all.iterrows():
            row_vals = [str(c).strip() for c in row.tolist()]
            if all(col in row_vals for col in expected_header):
                header_row_idx = idx
                break

        if header_row_idx is None:
            raise ValueError("Expected finance header row not found.")

        df = pd.read_excel(input_file, sheet_name=sheet_name,
                           header=header_row_idx, dtype=str)

    if payment_month and "Payment Month" in df.columns:
        df = df[df["Payment Month"] == payment_month]

    for col in ["Routing No", "Receiving A/C No", "Sender Account", "Mark"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "Credit Amount" in df.columns:
        df["Credit Amount"] = pd.to_numeric(
            df["Credit Amount"], errors="coerce").round(2)

    for dcol in ["Voucher Date", "Payment Date"]:
        if dcol in df.columns:
            df[dcol] = pd.to_datetime(
                df[dcol], errors="coerce").dt.strftime("%Y-%m-%d")

    if "Receiver Name" in df.columns:
        df["fin_ven"] = df["Receiver Name"].apply(derive_vendor)

    fin_uids = []
    bank = df["Sender Bank"].iloc[0] if "Sender Bank" in df.columns else "UNKNOWN"
    for idx, row in df.iterrows():
        rownum = str(idx + 1).zfill(6)
        payment_date_str = row.get("Payment Date", "")
        try:
            payment_dt = pd.to_datetime(payment_date_str)
            yyyymmdd = payment_dt.strftime("%Y%m%d")
            hexdate = format(int(yyyymmdd), "X")
        except Exception:
            hexdate = "UNKNOWN"
        try:
            amount = float(row.get("Credit Amount", 0))
            amount_int = int(amount)
            hexamount = format(amount_int, "X")
        except Exception:
            hexamount = "UNKNOWN"
        uid = f"F_{bank}_{hexdate}_{hexamount}_{rownum}"
        fin_uids.append(uid)

    df.insert(0, "fin_uid", fin_uids)

    df = df.rename(columns={
        "Routing No": "F_Routing_No",
        "Receiving A/C No": "F_Receiving_AC_No",
        "Credit Amount": "F_Credit_Amount",
        "Receiver Name": "F_Receiver_Name",
        "Bank Name": "F_Bank_Name",
        "Branch Name": "F_Branch_Name",
        "Sender Name": "F_Sender_Name",
        "Sender Account": "F_Sender_Account",
        "Sender Bank": "F_Sender_Bank",
        "Unit Name": "F_Unit_Name",
        "Team Name": "F_Team_Name",
        "New Project": "F_New_Project",
        "Project": "F_Project",
        "Sub Project": "F_Sub_Project",
        "PO": "F_PO",
        "Status": "F_Status",
        "Voucher Date": "F_Voucher_Date",
        "Voucher No": "F_Voucher_No",
        "Payment Date": "F_Payment_Date",
        "Payment Month": "F_Payment_Month",
        "Remarks": "F_Remarks",
        "Mark": "F_Mark",
        "Concern": "F_Concern"
    })

    return df
