import shutil
import os
import datetime
import configparser

# change dir to directory of this file so we can find the config file
os.chdir(os.path.dirname(os.path.abspath(__file__)))
config = configparser.ConfigParser()
config.read(R'backup_config.ini')

DB_LOCATION = config['DEFAULT']['db_location']
BACKUP_DIR = config['DEFAULT']['backup_dir']


def get_backup_file_list(backup_directory):
    '''
    Get a list of the files currently in the backup directory
    '''
    backup_files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if os.path.isfile(os.path.join(BACKUP_DIR, f))]
    
    return backup_files


def delete_oldest_backup(backup_file_list):
    '''
    Simply delete the oldest file in a list of files
    '''
    oldest_file = min(backup_file_list, key=os.path.getctime)
  
    os.remove(oldest_file)


def backup_db(db_location, backup_directory):
    '''
    Copy the database over to the backup directory and rename it with the backup date
    '''
    database_filename = os.path.basename(DB_LOCATION)
    backup_filename = '{}_{}'.format(datetime.date.today(), database_filename)

    backup_full_path = os.path.join(backup_directory, backup_filename)

    shutil.copy2(db_location, backup_full_path)


def main():
    backup_file_list = get_backup_file_list(BACKUP_DIR)

    backup_db(DB_LOCATION, BACKUP_DIR)

    if len(backup_file_list) > 4: # if there is more than 4 backup files in the backup directory 
        delete_oldest_backup(backup_file_list)
     
    
if __name__ == '__main__':
    main()
