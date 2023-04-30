import uvicorn


def serve_api():
    """This function targets api_endpoints.py as an application to host on uvicorns ASGI."""
    if __name__ == "__main__":
        uvicorn.run("api_endpoints:app", host="0.0.0.0", port=80, log_level="error")


serve_api()
