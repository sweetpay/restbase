test:
	pytest tests/

setupdev:
	pip install -r requirements.txt.dev

shell:
	ipython -i example.py

pypitest:
	python setup.py register -r pypitest
	python setup.py sdist upload -r pypitest

pypiprod:
	python setup.py register -r pypi
	python setup.py sdist upload -r pypi
