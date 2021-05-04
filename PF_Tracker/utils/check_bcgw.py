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

PFT_tracking = Base.classes.pf_tracking # map the pf_tracking table
REGION_FILE = Base.classes.pf_region_file   # map the pf_region_file table
session = Session(engine)

### BCGW location ############################################################
# cx_Oracle.init_oracle_client(lib_dir=) # the oracle quick client is needed here unless already available - gts has it so we don't need this at the moment
BCGW = config['DEFAULT']['BCGW_location']


def get_username_and_password():
    '''
    Get credentials to sign into the BCGW from a locked csv
    '''
    bcgw_mm_ts_up_csv = config['DEFAULT']['super_secret_csv']
    with open(bcgw_mm_ts_up_csv) as csv:
        uname, pword = csv.read().split(',')
    pword = pword.strip('\n')
    return uname, pword


def get_prov_forest(pf):
    '''
    Query the database and get all entries for a specific forest. Only used for testing in this script.
    '''
    db_entries = session.query(PFT_tracking).filter(PFT_tracking.prov_forest_name == pf).all()
    return db_entries


def get_db_entries():
    '''
    Query the database for all entries from the pf_tracking table
    '''
    db_entries = session.query(PFT_tracking).all()
    return db_entries


def get_bcgw_cursor():
    '''
    Connect to the BCGW and return a cursor to access data
    '''
    user, pword = get_username_and_password()
    conn = cx_Oracle.connect(user, pword, BCGW, encoding="UTF-8")
    cursor = conn.cursor()
    return cursor


def generate_sql(prov_forest=None, date_signed=None, document_type=None, deletion_number=None, pft=None):
    '''
    Generate an SQL statement based on the information available in the PF Tracker database. Search on as much matching
    data as possible from the PF Tracker without reducing it, if no match is found that means one of the database entries 
    contains an error.

    Args:
        prov_forest: prov_forest_name from PF Tracker db
        date_signed: date_signed from PF Tracker db
        document_type: document_type from PF Tracker db
        pft: pft from PF Tracker db
    Returns:
        sql: SQL statement based on information from PF Tracker db
        search (str): string that is entered into database, recording what information the search was based on
    '''
    sql = None
    search = None

    if date_signed:
        deletion_year = date_signed[:4] # don't get complicated in determining the year. Year is always the first 4 digits

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
    '''
    Query the database utilizing the cursor and the appropriate SQL statement. 
    Return 1 record if it matches
    '''
    cursor.execute(sql)

    return cursor.fetchone()


def update_database(id, bcgw_record, sql_query_criteria):
    '''
    Update PF Tracker database with information about the BCGW search
    '''
    pft_to_update = session.query(PFT_tracking).filter(PFT_tracking.id == id).first()

    if bcgw_record:
        pft_to_update.in_bcgw = 'Yes'
        pft_to_update.bcgw_sql_search = sql_query_criteria
    else: # This is not being used until some checks are completed on the BCGW/PF Tracker
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