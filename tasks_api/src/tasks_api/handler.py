"""AWS Lambda entry point for the task API."""

from mangum import Mangum

from tasks_api.main import app

handler = Mangum(app)
