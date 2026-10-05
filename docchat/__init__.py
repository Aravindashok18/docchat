import os

# Must be set before chromadb is imported anywhere: it otherwise tries to send telemetry.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
