.PHONY: run test reset evaluate measure rehearse
run:
	python3 portal/server.py
test:
	python3 -m unittest discover -s tests -v
reset:
	python3 -c "from portal.server import init_db; init_db(True); print('Demo fixtures reset')"
evaluate:
	python3 evaluation/run.py
measure:
	python3 evaluation/measure.py reports/measurement.json
rehearse:
	python3 demo/rehearse.py --iterations 3 --record
