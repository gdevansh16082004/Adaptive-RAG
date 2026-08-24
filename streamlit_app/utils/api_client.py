"""
API client for communicating with backend services.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

# Backend service URLs
RUST_BASE_URL = "http://localhost:8080/api"
PYTHON_BASE_URL = "http://127.0.0.1:8000"


def create_user(username: str, password: str, api_token: str) -> bool:
    """
    Create a new user account.

    Args:
        username: Username for the new account.
        password: Password for the new account.
        api_token: API token for authentication.

    Returns:
        True if user creation succeeds, False otherwise.
    """
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }
    logger.info("API Token received: %s", api_token)

    try:
        response = requests.post(
            f"{RUST_BASE_URL}/create_user",
            json={"username": username, "password": password},
            headers=headers,
        )

        logger.info("Calling /create_user, status code: %s", response.status_code)

        if response.status_code == 200:
            try:
                logger.debug("Create user response: %s", response.json())
            except ValueError:
                logger.warning("Create user returned non-JSON response")
            return True
        else:
            logger.error(
                "Create user failed: %s - %s",
                response.status_code,
                response.text
            )
            return False

    except requests.RequestException as e:
        logger.exception("Request to /create_user failed: %s", e)
        return False


def login_user(username: str, password: str, api_token: str) -> dict:
    """
    Authenticate user login.

    Args:
        username: Username to log in.
        password: Password for the user.
        api_token: API token for authentication.

    Returns:
        Response dictionary with JWT token if successful, None otherwise.
    """
    headers = {
        "X-API-TOKEN": api_token,
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{RUST_BASE_URL}/login",
        json={"username": username, "password": password},
        headers=headers,
    )
    logger.info("Calling /login, status code: %s", response.json())

    if response.status_code == 200:
        return response.json()

    return None


def get_api_token() -> str:
    """
    Get an API token for authentication.

    Returns:
        API token string if successful, None otherwise.
    """
    response = requests.post(f"{RUST_BASE_URL}/init")
    logger.info("Calling /init, status code: %s", response.json())

    if response.status_code == 200:
        return response.json()["api_token"]

    return None


def query_backend(query: str, session_id: str, user_id: str) -> str:
    """
    Send a query to the RAG backend on behalf of a user.

    Args:
        query: The user's query text.
        session_id: Session identifier for tracking conversation.
        user_id: Owner of the documents to search.

    Returns:
        Response text from the backend or error message.
    """
    url = f"{PYTHON_BASE_URL}/rag/query"
    print(f"[query_backend] Calling: {url}")

    response = requests.post(
        url,
        json={
            "query": query,
            "session_id": session_id,
            "user_id": user_id,
        },
        allow_redirects=False
    )

    if response.status_code == 200:
        return response.json()["result"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"


def document_upload_rag(file, description: str, user_id: str) -> bool:
    """
    Upload a document to the RAG system for a specific user.

    Args:
        file: File object to upload.
        description: Description of the document.
        user_id: Owner of the document.

    Returns:
        True if upload succeeds, False otherwise.
    """
    headers = {
        "X-Description": description,
        "X-User-ID": user_id,
    }
    url = f"{PYTHON_BASE_URL}/rag/documents/upload"

    if file:
        files = {"file": (file.name, file, file.type)}
        response = requests.post(url, files=files, headers=headers)
        print(response)

        if response.status_code in (200, 201):
            return True

    return False


def list_documents(user_id: str) -> list:
    """
    List the user's registered documents from the backend.

    Args:
        user_id: Owner of the documents.

    Returns:
        List of document records, empty on any failure.
    """
    try:
        response = requests.get(
            f"{PYTHON_BASE_URL}/rag/documents",
            headers={"X-User-ID": user_id},
        )
        if response.status_code == 200:
            return response.json()["documents"]
    except requests.RequestException as e:
        logger.exception("Listing documents failed: %s", e)
    return []


def delete_document(doc_id: str, user_id: str) -> bool:
    """
    Delete one of the user's documents and its vectors from the backend.

    Args:
        doc_id: ID of the document to delete.
        user_id: Owner of the document.

    Returns:
        True if deletion succeeds, False otherwise.
    """
    try:
        response = requests.delete(
            f"{PYTHON_BASE_URL}/rag/documents/{doc_id}",
            headers={"X-User-ID": user_id},
        )
        return response.status_code == 200
    except requests.RequestException as e:
        logger.exception("Deleting document failed: %s", e)
    return False
