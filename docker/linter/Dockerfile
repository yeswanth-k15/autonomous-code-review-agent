
FROM python:3.11-slim

WORKDIR /workspace

# Install only the required code-analysis tools.
RUN pip install --no-cache-dir \
    flake8==7.5.0 \
    black==26.10.1

# Create a non-root user.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin linter

# Use the non-root account by default.
USER 10001:10001

# Verify installed tools when the image is tested.
CMD ["sh", "-c", "flake8 --version && black --version"]
