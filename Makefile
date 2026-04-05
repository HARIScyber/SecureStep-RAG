run:
	poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-prod:
	poetry run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

test:
	poetry run pytest tests/ -v --cov=. --cov-report=term-missing

test-api:
	poetry run pytest tests/test_main_api.py -v

eval:
	poetry run python eval/ablation.py

benchmark:
	poetry run python eval/latency_benchmark.py

calibrate:
	poetry run python trust_filter/calibration.py --update-config --calibrate-weights

attack:
	poetry run python attack/corpus_injector.py

index:
	poetry run python vector_store/indexer.py

docker:
	docker compose up --build

docs:
	@echo "API Documentation at: http://localhost:8000/docs"
	@echo "ReDoc at: http://localhost:8000/redoc"
	@echo "Opening browser..."
	@poetry run python -c "import webbrowser; webbrowser.open('http://localhost:8000/docs')" &

frontend:
	cd frontend && npm install && npm run dev

dev:
	make docker & sleep 10 && make frontend

lint:
	poetry run ruff check . --fix

install:
	poetry install

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

.PHONY: run run-prod test test-api eval benchmark calibrate attack index docker docs health status config frontend dev lint install clean
