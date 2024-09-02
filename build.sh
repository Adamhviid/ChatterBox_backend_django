#!/bin/bash
# Activate the virtual environment
source ./venv/Scripts/activate

# Install the required packages
pip install -r requirements.txt

# Run database migrations
cd chatterbox_backend
python manage.py migrate
