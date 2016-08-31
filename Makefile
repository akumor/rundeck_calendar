.PHONY: init test

init: venv

test: init
	@echo "[ run unit tests ]"
	venv/bin/python -m tests.TestRundeckCalendar

clean:
	test -d venv && rm -rfv venv

venv: venv/bin/activate
venv/bin/activate: requirements.txt
	test -d venv || virtualenv -p python3 venv
	venv/bin/pip install -Ur requirements.txt
	touch venv/bin/activate
