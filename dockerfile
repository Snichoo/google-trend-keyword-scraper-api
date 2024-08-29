# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    xvfb \
    xauth \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN pip install --upgrade pip
RUN pip install playwright

# Install the browser binaries
RUN playwright install

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any Python dependencies in requirements.txt
RUN pip install -r requirements.txt

# Expose the port that Flask will run on
EXPOSE 5000

# Start Xvfb and the Flask server
CMD xvfb-run -a python api.py
