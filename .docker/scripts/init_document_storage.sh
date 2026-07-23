#!/bin/sh
set -eu

document_data_dir="src/django/.data/documents"

mkdir -p "${document_data_dir}/files"

# Production Django runs as UID 10001. Bind mounts retain host ownership, so
# grant the container account access without changing ownership of project files.
chmod -R a+rwX "${document_data_dir}"
