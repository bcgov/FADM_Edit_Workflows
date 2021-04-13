from flask import Flask, render_template, request, url_for, redirect, flash
from flaskwebgui import FlaskUI
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import func
from datetime import datetime, date
import getpass
import sys, os
import configparser

config = configparser.ConfigParser()

### This bit is so we can generate an exe as a single file. The app will need to know to go find the templates and static folders in 'sys._MEIPASS' and find the 'config.ini' file at the location of the exe.
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    config.read(os.path.join(os.path.dirname(sys.executable), 'config.ini'))
else:
    app = Flask(__name__)
    config.read('config.ini')

### CONNECT TO DB
db_location = config['DEFAULT']['db_location']
app.config['SQLALCHEMY_DATABASE_URI'] = Rf'sqlite:///{db_location}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

### ASSIGN DATABASE TABLES
db = SQLAlchemy(app)
Base = automap_base()
Base.prepare(db.engine, reflect=True)
PFT_tracking = Base.classes.pf_tracking
REGION_FILE = Base.classes.pf_region_file

###################################################################################################################################

def get_prov_forest(pf):
    db_entries = db.session.query(PFT_tracking).filter(PFT_tracking.prov_forest_name == pf).all()
    return db_entries


def get_pf_list():
    db_entries = db.session.query(PFT_tracking.prov_forest_name).distinct().all()
    return [pf[0] for pf in db_entries]


def get_forest_number(pf):
    db_entry = db.session.query(REGION_FILE).filter(REGION_FILE.prov_forest_name == pf).one()
    return db_entry.forest_number


@app.route('/', methods=['GET', 'POST'])
def index():
    prov_forests = get_pf_list()

    if request.method == 'POST':
        prov_forest = request.form['PF']
        return redirect(url_for('show_pf', prov_forest=prov_forest))
            
    return render_template('index.html', prov_forests=prov_forests)


@app.route('/view/<prov_forest>', methods=['GET', 'POST'])
def show_pf(prov_forest):
    if request.method == 'POST':
        prov_forest = request.form['PF']
        return redirect(url_for('show_pf', prov_forest=prov_forest))
    
    prov_forests = get_pf_list()
    pf_db_data = get_prov_forest(prov_forest)
    forest_number = get_forest_number(prov_forest)

    return render_template('index.html', prov_forests=prov_forests, pf_db_data=pf_db_data, prov_forest=prov_forest, forest_number=forest_number)


@app.route('/add/<prov_forest>', methods=['GET', 'POST'])
def add_new_pft(prov_forest):
    
    if request.method == 'POST':
        try:
            pft = request.form.get('pft', type=int)
            lands_file = request.form.get('lands_file') or None
            legal_desc = request.form.get('legal') or None
            date_rec = request.form.get('date_rec') or None
            area = request.form.get('area', type=float) or None
            purpose = request.form.get('purpose') or None
            notes = request.form.get('notes') or None

            new_entry = PFT_tracking(prov_forest_name=prov_forest, 
                                        prov_forest_tracking_num=pft, 
                                        lands_file=lands_file, 
                                        legal_description=legal_desc,
                                        date_received=date_rec,
                                        ha_deleted=area,
                                        purpose=purpose,
                                        notes=notes,
                                        date_last_edited=datetime.today().strftime('%Y-%m-%d'),
                                        last_edited_by=getpass.getuser())
            db.session.add(new_entry)
            db.session.commit()
            flash('PFT successfully created', 'success') 
        except:
            flash('Error creating PFT', 'error')

        return redirect(url_for('show_pf', prov_forest=prov_forest))

    forest_number = get_forest_number(prov_forest)

    db_entries = get_prov_forest(prov_forest)
    pfts = [entry.prov_forest_tracking_num for entry in db_entries if entry.prov_forest_tracking_num != None]
    new_pft_num = max(pfts) + 1
    return render_template('add.html', new_pft_num=new_pft_num, prov_forest=prov_forest, forest_number=forest_number)


@app.route('/delete/<prov_forest>/<int:id>')
def delete(prov_forest, id):
    pft_to_delete = db.session.query(PFT_tracking).filter(PFT_tracking.id==id).delete()
    db.session.commit()

    return redirect(url_for('show_pf', prov_forest=prov_forest))


@app.route('/update/<prov_forest>/<int:id>', methods=['GET','POST'])
def update(prov_forest, id):
    pft_to_update = db.session.query(PFT_tracking).filter(PFT_tracking.id == id).first()

    if request.method == 'POST':
        pft = request.form.get('pft', type=int)
        lands_file = request.form.get('lands_file') or None
        legal_desc = request.form.get('legal') or None
        date_rec = request.form.get('date_rec') or None
        area = request.form.get('area', type=float) or None
        document_type = request.form.get('doc_type') or None
        deletion_number = request.form.get('del_num') or None
        purpose = request.form.get('purpose') or None
        date_signed = request.form.get('date_signed') or None
        notes = request.form.get('notes') or None

        pft_to_update.legal_description = legal_desc
        pft_to_update.lands_file = lands_file
        pft_to_update.date_received = date_rec
        pft_to_update.ha_deleted = area
        pft_to_update.document_type = document_type
        pft_to_update.deletion_number = deletion_number
        pft_to_update.purpose = purpose
        pft_to_update.notes = notes
        pft_to_update.date_signed = date_signed
        pft_to_update.date_last_edited = datetime.today().strftime('%Y-%m-%d')
        pft_to_update.last_edited_by = getpass.getuser()

        db.session.commit()
        flash('Record successfully updated', 'success')
        return redirect(url_for('show_pf', prov_forest=prov_forest))

    else:
        return render_template('update.html', pft_to_update=pft_to_update, prov_forest=prov_forest)


@app.route('/updates_in_progress', methods=['GET','POST'])
def updates_in_progress():
    received_cut_off_date = date(year=2019, month=1, day=1)

    updates_in_progress = db.session.query(PFT_tracking).filter(PFT_tracking.ministerial_order == None, PFT_tracking.date_received >= received_cut_off_date).order_by(PFT_tracking.date_received).all()

    return render_template('updates_in_progress.html', updates_in_progress=updates_in_progress)


if __name__=="__main__":
    import encodings.idna

    app.secret_key='abf11811c65e3ba0341a9fa7701ca0f5'
    app.run(debug=True)

    # ui = FlaskUI(app)
    # ui.app_mode=False
    # ui.run()
