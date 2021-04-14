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