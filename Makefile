install:
	pip3 install -r requirements.txt

run:
	python3 manage.py runserver 0.0.0.0:6660

migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

shell:
	python3 manage.py shell
