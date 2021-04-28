# Provincial Forest Tracker

An app built in Python for tracking Provincial Forest deletions in BC. 
This app is built with Flask, though it is not being deployed as a web application. [flaskwebgui](https://github.com/ClimenteA/flaskwebgui) is being used to make this Flask app run as a desktop application with the front-end built with HTML/CSS.

## Prerequisites

- Python 3.6+

## Requirements 

```
pip install Flask
pip install Flask-SQLAlchemy
pip install flaskwebgui

or

pip install -r requirements.txt
```

It is recommended to create a virtual environment with venv when setting up your Flask project. Pyinstaller is used to build an executable of this program for distribution and will also need to be installed in your virtual environment.

## Usage

If you are continuing development of this app, it is important to note the ways in which the app can run.  The main function contains 2 different ways of running the app; 1 for development and 1 for deployment. 

For development, the main function should be run in this configuration, which runs the app in Flask's debug mode allowing changes in the app to be viewed instantly:
```
app.run(debug=True)

# ui = FlaskUI(app)
# ui.app_mode=False
# ui.run()
```

For app deployment, the main function should be run in this configuration, allowing flaskwebgui to load the app automatically as a pseudo desktop app:
```
# app.run(debug=True)

ui = FlaskUI(app)
ui.app_mode=False
ui.run()
```

## Database

The Provincial Forest Tracker database is a simple SQLite database. It includes all the fields that were previously captured by the Provincial Forest tracking spreadsheet, along with new fields created to add functionality in tracking and reporting PF deletion status and history. Many of these fields are not used in the front-end application but are preserved for record keeping purposes. These fields and their simple relationships can be seen in Figure 1.

These database fields all have datatypes that can be viewed by examining the database (I recommend [DB Browser for SQLite](https://sqlitebrowser.org/)). Even though these fields are designated as TEXT, INTEGER, REAL, etc, SQLite does not inherently check data being entered into the database. This means any values can be placed into any column (Ex. The string ‘Hello’ could be placed into a field with datatype INTEGER). This can either be an annoying or a handy feature of SQLite depending on usage. For example, it is beneficial for our team to be able to put the string ‘Cancelled’ into the ‘deletion_number’ [INTEGER] column to signify a specific deletion was cancelled. The HTML input forms handle restricting input where needed.

<p align="center">
  <img src="images/PF_ERD.png" />
</p>

## Building the EXE