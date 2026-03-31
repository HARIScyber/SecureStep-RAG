run:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-prod:
	python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

test:
	pytest tests/

test-api:
	pytest tests/test_main_api.py -v

eval:
	python eval/ablation.py

benchmark:
	python eval/latency_benchmark.py

calibrate:
	python trust_filter/calibration.py --update-config --calibrate-weights

attack:
	python attack/corpus_injector.py

index:
	python vector_store/indexer.py

docker:
	docker compose up --build

docs:
	@echo "API Documentation at: http://localhost:8000/docs"
	@echo "ReDoc at: http://localhost:8000/redoc"
	@echo "Opening browser..."
	@python -c "import webbrowser; webbrowser.open('http://localhost:8000/docs')" &

health:
	curl http://localhost:8000/health && echo ""

status:
	curl http://localhost:8000/api/status && echo ""

config:
	curl http://localhost:8000/api/config && echo ""

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/

.PHONY: run run-prod test test-api eval benchmark calibrate attack index docker docs health status config clean
