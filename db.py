from sqlalchemy import create_engine, Table, Column, String, MetaData , Text,text
from sqlalchemy.schema import CreateTable
import os
from dotenv import load_dotenv
load_dotenv()  # 讀取 .env 文件中的環境變數
import pandas as pd
def init_db():
    # Replace the following values based on your database connection details

    username = os.getenv('DB_USERNAME', 'default_username')
    password = os.getenv('DB_PASSWORD', 'default_password')
    host = os.getenv('DB_HOST', 'default_host')
    database = os.getenv('DB_DATABASE', 'default_database')
    # Create database URL
    database_url = f'mysql+pymysql://{username}:{password}@{host}/{database}'

    # Create engine
    engine = create_engine(database_url)
    return engine


def create_table(columns, table_name):
    metadata = MetaData()
    engine = init_db()
    table = Table(
        table_name, metadata,
        *(Column(col, Text) for col in columns)
    )

    metadata.create_all(engine)


def Insert_data(table,all_data):
    all_data.to_sql(name=f'{table}', con=init_db(), if_exists='append', index=False)

def Delete_Existing_Records(table,data,key_col):

    engine = init_db()
    key_data = tuple(data[f'{key_col}'].unique())  # Convert to list

    if not key_data:
        return  # Exit if no names to delete

    # Prepare the query using bind parameters with expanding
    delete_query = text( f"DELETE FROM {table} WHERE {key_col} IN :{key_col}")
    #delete_query = delete_query.bindparams(bindparam('pdf_names', expanding=True))

    with engine.connect() as connection:
        result = connection.execute(delete_query, {f'{key_col}': key_data})
        connection.commit()  # 確保提交事務


# def generate_unique_id(prefix='A'):
#     # Get the current time in seconds since the epoch
#     current_time = int(time.time() * 1000)
#     # Convert the current time to a string and prepend the prefix
#     unique_id = f"{prefix}{current_time}"
#     return unique_id


''''''
def check_assistantid(table,key_col,value):
    engine = init_db()
    select_query = text(f"SELECT assistantid  FROM {table} WHERE {key_col} = :{key_col}")
    with engine.connect() as connection:
        result = connection.execute(select_query, {f'{key_col}': value})
        for row in result:
            return row[0]





def select_all(table):
    engine = init_db()
    select_query = text(f"SELECT * FROM {table} ")
    df = pd.read_sql(select_query, engine)
    return df

def select_user(table,username):
    engine = init_db()
    select_query = text(f"SELECT * FROM {table} where username = {username} LIMIT 1 ")
    df = pd.read_sql(select_query, engine)
    return df



import json
def select_part_sql(query):
    engine = init_db()
    try:
        print(query)
        df = pd.read_sql(query, engine)
        result_dict = df.to_dict(orient='records')
        result_json = json.dumps(result_dict, ensure_ascii=False, indent=4)
        return result_json
    except Exception as e:
        print(f"Error executing query: {e}")
        return None
def select_part_v(table, **conditions):
    engine = init_db()
    if table == '0':
        table = 'capacitor_info'
    else:
        table = 'mosfet_info'

    where_clauses = []
    for key, value in conditions.items():
        try:
            if '~' in value:
                min_val, max_val = map(float, value.split('~'))
                where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) >= '{min_val}'")
                where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) <= '{max_val}'")
            elif '>=' in value:
                val = (value.split('>=')[1])
                where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) >= '{val}'")
            elif '<=' in value:
                val = (value.split('<=')[1])
                where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) <= '{val}'")
            elif '>' in value:
                val = (value.split('>')[1])
                where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) > '{val}'")
            elif '<' in value:
                val = (value.split('<')[1])
                where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) < '{val}'")

            else:
                if value.isdigit():
                    if '!=' in value:
                        val = (value.split('!=')[1])
                        where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) NOT LIKE '%{val}%'")
                    else:
                        where_clauses.append(f"CAST({key} AS DECIMAL(10, 3)) = '{value}'")
                else:
                    if 'NULL' in value:
                        where_clauses.append(f"{key} is {value}")
                    elif '!=' in value:
                        val = (value.split('!=')[1])
                        where_clauses.append(f"{key} NOT LIKE '%{val}%'")
                    else:
                        where_clauses.append(f"{key}  = '{value}'")

        except Exception as e:
            print(f"Error processing condition {key}: {e}")
            continue

    where_clause = " AND ".join(where_clauses)
    if where_clauses:
        select_query = text(f"SELECT * FROM {table} WHERE {where_clause} ORDER BY RAND() LIMIT 30 ")
    else:
        return None

    try:
        print(select_query)
        df = pd.read_sql(select_query, engine, params=conditions)
        result_json = df.to_json(orient='records', force_ascii=False)
        return result_json
    except Exception as e:
        print(f"Error executing query: {e}")
        return None



# filename = '金氧半電晶體_v2'
# excel_file_path = rf'C:\Users\Hopper_Chen\Desktop\new\{filename}.xlsx'
#
# def insertfromExcel(excel_file_path):
#     all_data = pd.read_excel(excel_file_path, sheet_name='工作表1')
#     Insert_data('mosfet_info',all_data)
#

import re

def select_report_v(**conditions):
    engine = init_db()
    PdfPages_8d = 'PdfPages_8d'
    #PDFInfo = 'PDFInfo'

    pattern = re.compile("^[A-Za-z_]+$")
    for key, value in conditions.items():
        if pattern.match(value):
            value = value.lower()
            conditions[key] = f"{value} "

    where_clauses = [f"page_text like '%{value}%'" for key, value in conditions.items()]
    where_clause = " AND ".join(where_clauses)
    if where_clauses:
        select_query = text(f"SELECT filename,doc_number,description FROM {PdfPages_8d} WHERE {where_clause}")
    else:
        return None
    # 执行查询并将结果转换为JSON
    df = pd.read_sql(select_query, engine, params=conditions)
    result_json = df.to_json(orient='records', force_ascii=False)
    return result_json
