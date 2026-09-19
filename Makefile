test:
	python -m pytest -q

verify:
	python verify.py
	python -m compileall -q ai core platform eval run.py

score:
	python -m eval.score

demo:
	python run.py case "I did not make the ACH payment of £1250 on 2026-01-02 to Northwind."
