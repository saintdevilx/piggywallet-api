
## clone the git repo
`git clone https://bitbucket.org/mpwtechwarriors/mpw-django.git`

## create virtual environment

	1.`pip install virtualenv`
	2. virtualenv mpw-venv
	3. source mpw-venv

**everytime you want to run django server make sure you have enabled the virtual env



## change to project directory

`cd MPW-django`

## download local settings file to avoid conflict with prouction settings

[dowload localised_settings.py](https://slack-files.com/TRGBNM2A2-FR6SS577T-3076603873)

copy the `localised_settings.py` to MPW-django **->** mpw
 ** DON'T MAKE ANY CHANGES TO `settings.py`



## install python dependency to run the django project
`pip install -r requirements.txt`



## install postgres 10 or 10+
[follow this tutorial to install postgres on ubuntu](https://www.liquidweb.com/kb/install-and-connect-to-postgresql-10-on-ubuntu-16-04/)


## create database on postgres to get started
[creating database on postgres](https://www.guru99.com/postgresql-create-database.html)

update the database name in localised_settings.py

SETTINGS ={
    ....
	NAME:"<database base name you created>"
	....
}

## migrate the database changes
`python manage.py migrate`

## run the development server using
`python manage.py runserver` by default will run on localhost:8000

## run server on global port
`python manage.py runserver 0.0.0.0:<portnumber>`
