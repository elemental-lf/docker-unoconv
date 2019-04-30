up:
	docker-compose up -d --scale worker=3 --remove-orphans
	./create-buckets.sh

down:
	docker-compose down --remove-orphans

.PHONY: up down
