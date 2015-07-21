


The Django application can be controlled using the manage.py application.

Some usefull commands:

./manage.py runserver       # Run the server, as configured
./manage.py makemigrations  # Create code to migrate the database to its current model
./manage.py migrate         # Perform the necessary database migrations
./manage.py test            # Run the tests
./manage.py startapp        # Create a skeleton for a new app
./manage.py startproject    # Create a skeleton for a complete project
./manage.py createsuperuser # Create a superuser for a project


Full documentation can be found at https://docs.djangoproject.com/en/1.8/ref/django-admin/


Advantages of Django:

 * Very well integrated database ORM
 * ORM is more pythonic than SQLAlchemy
 * ORM able to migrate itself to a new version
 * Testing suite allows easy testing, including sandbox databases.
 * Many modules available, e.g. Rest Framework
 * Ability to generate generic forms for database objects
 * Built-in powerful template language

Disadvantages:
 * ORM less capable than SQLAlchemy, but sufficient for most uses
 * Template language overlaps template syntax for AngularJS