# Define instance as a variable passed via command line
INSTANCE ?= astropy__astropy-12907
IMAGE_NAME ?= swe-agent
OUTPUT_DIR ?= $(PWD)/output

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

ENV_FILE ?= .env.docker

# Run the agent for a given instance
run: build
	mkdir -p $(OUTPUT_DIR)
	docker run --rm \
		--env-file $(ENV_FILE) \
		-v $(OUTPUT_DIR):/app/output \
		$(IMAGE_NAME) python src/main.py --instance_id=$(INSTANCE)


# Clean local output
clean:
	rm -rf $(OUTPUT_DIR)
