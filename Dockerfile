# Use a slim Python base image for smaller image size
FROM python:3.11-slim-buster

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PATH="/home/user/.local/bin:$PATH"
#    CHAINLIT_HOST=0.0.0.0 \
#    CHAINLIT_PORT=8000

# Create a non-root user for security best practices

RUN useradd -m -u 1000 user
USER user

# Set the working directory inside the container
WORKDIR /home/user/app

# Copy the requirements file first to leverage Docker's caching
COPY --chown=user requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY --chown=user . .

# Expose the port Chainlit will run on
EXPOSE 8000

# Command to run your Chainlit application
# Always add -h for production deployments to prevent browser opening
# and --host 0.0.0.0 for Docker to bind to all network interfaces.

# Command to run your Chainlit application
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000", "-h"]