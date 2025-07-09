-- CREATE DATABASE
CREATE DATABASE IF NOT EXISTS bank_reconciliation;
USE bank_reconciliation;

-- bank_data TABLE FOR PARSED BANK STATEMENTS
CREATE TABLE IF NOT EXISTS bank_data (
    bank_id INT AUTO_INCREMENT PRIMARY KEY,
    bank_uid VARCHAR(50) NOT NULL UNIQUE,
    B_Date DATE,
    B_Particulars VARCHAR(255),
    B_Ref_Cheque VARCHAR(50),
    B_Withdrawal DECIMAL(18,2),
    B_Deposit DECIMAL(18,2),
    B_Balance DECIMAL(18,2),
    bank_ven VARCHAR(255),
    acct_no VARCHAR(50),
    bank_code VARCHAR (10),
    statement_month VARCHAR(20),
    statement_year VARCHAR(10),
    bf_is_matched TINYINT DEFAULT 0,
	bf_date_matched DATETIME DEFAULT NULL,
	bft_is_matched TINYINT DEFAULT 0,
    bft_date_matched DATETIME DEFAULT NULL,
    input_date DATETIME
);

-- fin_data TABLE FOR PARSED FINANCE RECORDS
CREATE TABLE IF NOT EXISTS fin_data (
    fin_id INT AUTO_INCREMENT PRIMARY KEY,
    fin_uid VARCHAR(50) NOT NULL UNIQUE,
    F_Routing_No VARCHAR(50),
    F_Receiving_AC_No VARCHAR(50),
    F_Credit_Amount DECIMAL(18,2),
    F_Receiver_Name VARCHAR(255),
    F_Bank_Name VARCHAR(255),
    F_Branch_Name VARCHAR(255),
    F_Sender_Name VARCHAR(255),
    F_Sender_Account VARCHAR(50),
    F_Sender_Bank VARCHAR(255),
    F_Unit_Name VARCHAR(255),
    F_Team_Name VARCHAR(255),
    F_New_Project VARCHAR(255),
    F_Project VARCHAR(255),
    F_Sub_Project VARCHAR(255),
    F_PO VARCHAR(255),
    F_Status VARCHAR(255),
    F_Voucher_Date DATE,
    F_Voucher_No VARCHAR(255),
    F_Payment_Date DATE,
    F_Payment_Month VARCHAR(255),
    F_Remarks TEXT,
    F_Mark VARCHAR(255),
    F_Concern VARCHAR(255),
    fin_ven VARCHAR(255),
	bf_is_matched TINYINT DEFAULT 0,
	bf_date_matched DATETIME DEFAULT NULL,
	bft_is_matched TINYINT DEFAULT 0,
    bft_date_matched DATETIME DEFAULT NULL,
	input_date DATETIME
);

-- tally_data TABLE FOR PARSED TALLY LEDGERS
CREATE TABLE IF NOT EXISTS tally_data (
    tally_id INT AUTO_INCREMENT PRIMARY KEY,
    tally_uid VARCHAR(50) NOT NULL UNIQUE,
    T_Date DATE,
    dr_cr VARCHAR(255),
    T_Particulars TEXT,
    T_Vch_Type VARCHAR(255),
    T_Vch_No VARCHAR(255),
    T_Debit DECIMAL(18,2),
    T_Credit DECIMAL(18,2),
    tally_ven TEXT,
    acct_no VARCHAR(50),
    bank_code VARCHAR(255),
    unit_name VARCHAR(255),
	statement_month VARCHAR(20),
    statement_year VARCHAR(10),
    is_matched_bft TINYINT DEFAULT 0,
	date_matched_bft DATETIME DEFAULT NULL,
    input_date DATETIME
);

-- BANK FINANCE MATCHED DATA: bf_matched TABLE FOR BANK FINANCE MATCHED DATA
CREATE TABLE IF NOT EXISTS bf_matched (
    -- Match metadata columns
	bf_id INT AUTO_INCREMENT PRIMARY KEY,
	bf_match_id VARCHAR(50) NOT NULL,
    bf_source VARCHAR(16) NOT NULL,
    bf_match_type VARCHAR(32),
	bf_is_matched TINYINT DEFAULT 0,
	bf_date_matched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Bank columns (same as in bank_data)
    bank_id INT, -- Source sql id reference column
    bank_uid VARCHAR(50),
    B_Date DATE,
    B_Particulars VARCHAR(255),
    B_Ref_Cheque VARCHAR(50),
    B_Withdrawal DECIMAL(18,2),
    B_Deposit DECIMAL(18,2),
    B_Balance DECIMAL(18,2),
    bank_ven VARCHAR(255),
	bank_code VARCHAR(8),
    acct_no VARCHAR(50),
    statement_month VARCHAR(20),
    statement_year VARCHAR(10),

    -- Finance columns (same as in fin_data)
	fin_id INT, -- Source sql id reference column
    fin_uid VARCHAR(50),
    F_Routing_No VARCHAR(50),
    F_Receiving_AC_No VARCHAR(50),
    F_Credit_Amount DECIMAL(18,2),
    F_Receiver_Name VARCHAR(255),
    F_Bank_Name VARCHAR(255),
    F_Branch_Name VARCHAR(255),
    F_Sender_Name VARCHAR(255),
    F_Sender_Account VARCHAR(50),
    F_Sender_Bank VARCHAR(255),
    F_Unit_Name VARCHAR(255),
    F_Team_Name VARCHAR(255),
    F_New_Project VARCHAR(255),
    F_Project VARCHAR(255),
    F_Sub_Project VARCHAR(255),
    F_PO VARCHAR(255),
    F_Status VARCHAR(255),
    F_Voucher_Date DATE,
    F_Voucher_No VARCHAR(255),
    F_Payment_Date DATE,
    F_Payment_Month VARCHAR(255),
    F_Remarks TEXT,
    F_Mark VARCHAR(255),
    F_Concern VARCHAR(255),
    fin_ven VARCHAR(255),
	input_date DATETIME,

	bft_is_matched TINYINT DEFAULT 0,
	bft_date_matched DATETIME DEFAULT NULL
    );

-- BANK FINANCE TALLY MATCHED DATA: bft_matched TABLE FOR BANK FINANCE TALLY MATCHED DATA
CREATE TABLE IF NOT EXISTS bft_matched (
    bft_id INT AUTO_INCREMENT PRIMARY KEY,

    -- Match metadata columns
    bft_match_id VARCHAR(50) NOT NULL,
    bft_source VARCHAR(16) NOT NULL,
    bft_match_type VARCHAR(32),

	bf_id INT,
	bf_is_matched TINYINT DEFAULT 0,
	bf_match_id VARCHAR(50),
    bf_source VARCHAR(16),
    bf_match_type VARCHAR(32),
    bf_date_matched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Bank columns (same as in bank_data)
    bank_id INT, -- Source sql id reference column
    bank_uid VARCHAR(50),
    B_Date DATE,
    B_Particulars VARCHAR(255),
    B_Ref_Cheque VARCHAR(50),
    B_Withdrawal DECIMAL(18,2),
    B_Deposit DECIMAL(18,2),
    B_Balance DECIMAL(18,2),
    bank_ven VARCHAR(255),
    acct_no VARCHAR(50),

    -- Finance columns (same as in fin_data)
	fin_id INT, -- Source sql id reference column
    fin_uid VARCHAR(50),
    F_Routing_No VARCHAR(50),
    F_Receiving_AC_No VARCHAR(50),
    F_Credit_Amount DECIMAL(18,2),
    F_Receiver_Name VARCHAR(255),
    F_Bank_Name VARCHAR(255),
    F_Branch_Name VARCHAR(255),
    F_Sender_Name VARCHAR(255),
    F_Sender_Account VARCHAR(50),
    F_Sender_Bank VARCHAR(255),
    F_Unit_Name VARCHAR(255),
    F_Team_Name VARCHAR(255),
    F_New_Project VARCHAR(255),
    F_Project VARCHAR(255),
    F_Sub_Project VARCHAR(255),
    F_PO VARCHAR(255),
    F_Status VARCHAR(255),
    F_Voucher_Date DATE,
    F_Voucher_No VARCHAR(255),
    F_Payment_Date DATE,
    F_Payment_Month VARCHAR(255),
    F_Remarks TEXT,
    F_Mark VARCHAR(255),
    F_Concern VARCHAR(255),
    fin_ven VARCHAR(255),
    
    -- Tally columns (same as tally_data)
    tally_id INT,
    tally_uid VARCHAR(50),
    T_Date DATE,
    dr_cr VARCHAR(255),
    T_Particulars TEXT,
    T_Vch_Type VARCHAR(255),
    T_Vch_No VARCHAR(255),
    T_Debit DECIMAL(18,2),
    T_Credit DECIMAL(18,2),
    tally_ven TEXT,
    bank_code VARCHAR(255),
    unit_name VARCHAR(255),
	statement_month VARCHAR(20),
    statement_year VARCHAR(10),
    input_date DATETIME,

    -- Matched flags for BFT
    is_matched_bft TINYINT DEFAULT 0,
    date_matched_bft DATETIME NULL,
    is_matched TINYINT DEFAULT 0
);

-- BANK TALLY MATCHED DATA: bt_matched TABLE FOR BANK TALLY MATCHED DATA
CREATE TABLE bt_matched (
	bt_id INT AUTO_INCREMENT PRIMARY KEY,

    -- Bank columns
    bank_id INT,
    bank_uid VARCHAR(50),
    B_Date DATE,
    B_Particulars VARCHAR(255),
    B_Ref_Cheque VARCHAR(50),
    B_Withdrawal DECIMAL(18,2),
    B_Deposit DECIMAL(18,2),
    B_Balance DECIMAL(18,2),
    bank_ven VARCHAR(255),
    acct_no VARCHAR(50),
    bank_code VARCHAR(10),
    statement_month VARCHAR(20),
    statement_year VARCHAR(10),
    bf_is_matched TINYINT,
    bf_date_matched DATETIME,
    input_date DATETIME,

    cheque_ref VARCHAR(50),
    bt_match_id VARCHAR(50),
    bt_source VARCHAR(50),

    -- Tally columns
    tally_id INT,
    tally_uid VARCHAR(50),
    T_Date DATE,
    dr_cr VARCHAR(255),
    T_Particulars TEXT,
    T_Vch_Type VARCHAR(255),
    T_Vch_No VARCHAR(255),
    T_Debit DECIMAL(18,2),
    T_Credit DECIMAL(18,2),
    tally_ven TEXT,
    unit_name VARCHAR(255),
    is_matched_bft TINYINT,
    date_matched_bft DATETIME
);

CREATE TABLE IF NOT EXISTS bank_accounts (
    acct_no VARCHAR(64) NOT NULL,
    bank_code VARCHAR(8) NOT NULL,
    PRIMARY KEY (acct_no, bank_code)
);

