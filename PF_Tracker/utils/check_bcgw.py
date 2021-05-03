import configparser
import os
import cx_Oracle
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import datetime

# Read config file
os.chdir(os.path.dirname(os.path.abspath(__file__)))
config = configparser.ConfigParser()
config.read('backup_config.ini')

# CONNECT TO PF TRACKING DATABASE ######################################################
db_location = config['DEFAULT']['db_location']
engine = create_engine(Rf'sqlite:///{db_location}')
Base = automap_base()
Base.prepare(engine, reflect=True)

PFT_tracking = Base.classes.pf_tracking
REGION_FILE = Base.classes.pf_region_file
session = Session(engine)

### BCGW CREDENTIALS ############################################################
# cx_Oracle.init_oracle_client(lib_dir=)
BCGW = config['DEFAULT']['BCGW_location']


def get_username_and_password():
    bcgw_mm_ts_up_csv = config['DEFAULT']['super_secret_csv']
    with open(bcgw_mm_ts_up_csv) as csv:
        uname, pword = csv.read().split(',')
    pword = pword.strip('\n')
    return uname, pword


def get_prov_forest(pf):
    db_entries = session.query(PFT_tracking).filter(PFT_tracking.prov_forest_name == pf).all()
    return db_entries


def get_db_entries():
    db_entries = session.query(PFT_tracking).all()
    return db_entries


def get_bcgw_cursor():
    user, pword = get_username_and_password()
    conn = cx_Oracle.connect(user, pword, BCGW, encoding="UTF-8")
    cursor = conn.cursor()
    return cursor


def generate_sql(prov_forest=None, date_signed=None, document_type=None, deletion_number=None, pft=None):
    sql = None
    search = None

    if date_signed:
        deletion_year = date_signed[:4]

    if date_signed and document_type:
        sql = f"""select PROV_FOREST_CD_DESCRIPTION, DOCUMENT_TYPE, DELETION_YEAR, DELETION_NUMBER
                from WHSE_ADMIN_BOUNDARIES.FADM_PROV_FOREST_DELETION
                where PROV_FOREST_CD_DESCRIPTION = '{prov_forest}' AND
                DOCUMENT_TYPE = '{document_type}' AND DELETION_YEAR = '{deletion_year}' AND
                DELETION_NUMBER = '{deletion_number}'
                """
        search = 'Year/DocType/Del_Num'
    elif date_signed and not document_type:
        sql = f"""select PROV_FOREST_CD_DESCRIPTION, DOCUMENT_TYPE, DELETION_YEAR, DELETION_NUMBER
                from WHSE_ADMIN_BOUNDARIES.FADM_PROV_FOREST_DELETION
                where PROV_FOREST_CD_DESCRIPTION = '{prov_forest}' AND
                DELETION_YEAR = {deletion_year} AND
                DELETION_NUMBER = {pft}
                """
        search = 'Year/PFT'
    elif document_type and deletion_number:
        sql = f"""select PROV_FOREST_CD_DESCRIPTION, DOCUMENT_TYPE, DELETION_YEAR, DELETION_NUMBER
                from WHSE_ADMIN_BOUNDARIES.FADM_PROV_FOREST_DELETION
                where PROV_FOREST_CD_DESCRIPTION = '{prov_forest}' AND
                DOCUMENT_TYPE = '{document_type}' AND
                DELETION_NUMBER = {deletion_number}
                """
        search = 'DocType/Del_Num'
    else:
        sql = f"""select PROV_FOREST_CD_DESCRIPTION, DOCUMENT_TYPE, DELETION_YEAR, DELETION_NUMBER
                from WHSE_ADMIN_BOUNDARIES.FADM_PROV_FOREST_DELETION
                where PROV_FOREST_CD_DESCRIPTION = '{prov_forest}' AND
                DELETION_NUMBER = {pft}
                """
        search = 'PFT'
    
    
    return sql, search


def query_bcgw(cursor, sql):
    cursor.execute(sql)

    return cursor.fetchone()


def update_database(id, bcgw_record, sql_query_criteria):
    pft_to_update = session.query(PFT_tracking).filter(PFT_tracking.id == id).first()

    if bcgw_record:
        pft_to_update.in_bcgw = 'Yes'
        pft_to_update.bcgw_sql_search = sql_query_criteria
    else: 
        pft_to_update.in_bcgw = 'No'

    session.commit()

    
def main():
    cursor = get_bcgw_cursor()
    entries = get_db_entries()

    not_in_bcgw = 0

    for entry in entries:
        sql, search = generate_sql(prov_forest=entry.prov_forest_name, date_signed=entry.date_signed, document_type=entry.document_type, 
                deletion_number=entry.deletion_number, pft=entry.prov_forest_tracking_num)
        
        if sql:
            result = query_bcgw(cursor, sql)
            # print(f'{entry.id} {entry.prov_forest_name} - {entry.prov_forest_tracking_num} - {entry.date_signed} ::::: {result} :::: {search}')
            if result == None:
                not_in_bcgw += 1
            else:
                update_database(entry.id, result, search)
    print(f'Not in BCGW: {not_in_bcgw}')
            

if __name__=='__main__':
    main()