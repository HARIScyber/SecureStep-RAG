run:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/

eval:
	python eval/ablation.py

attack:
	python attack/corpus_injector.py

index:
	python vector_store/indexer.py

docker:
	docker compose up --build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
