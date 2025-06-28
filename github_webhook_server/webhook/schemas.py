"""
Pydantic models for request and response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    """
    Schema for creating a new client.
    """
    name: str = Field(..., description="Client name", example="my-client")
    description: Optional[str] = Field(None, description="Client description", example="My webhook client")
    interested_orgs: Optional[List[str]] = Field(None, description="List of GitHub organizations to watch", example=["microsoft", "google"])
    interested_repos: Optional[List[str]] = Field(None, description="List of GitHub repositories to watch", example=["microsoft/vscode", "google/gson"])


class ClientResponse(BaseModel):
    """
    Schema for client response.
    """
    id: int = Field(..., description="Client ID")
    name: str = Field(..., description="Client name")
    description: Optional[str] = Field(None, description="Client description")
    interested_orgs: List[str] = Field([], description="List of GitHub organizations to watch")
    interested_repos: List[str] = Field([], description="List of GitHub repositories to watch")
    created_at: datetime = Field(..., description="Client creation timestamp")
    last_poll_at: Optional[datetime] = Field(None, description="Last poll timestamp")


class PollResponse(BaseModel):
    """
    Schema for poll response.
    """
    client_id: int = Field(..., description="Client ID")
    messages: List[Dict[str, Any]] = Field(..., description="List of new webhook messages")
    total_new_messages: int = Field(..., description="Total number of new messages")
    poll_timestamp: datetime = Field(..., description="Poll timestamp")


class WebhookEvent(BaseModel):
    """
    Schema for webhook event.
    """
    event_type: str = Field(..., description="GitHub event type", example="push")
    delivery_id: Optional[str] = Field(None, description="GitHub delivery ID", example="72d3162e-cc78-11e3-81ab-4c9367dc0958")
    signature: Optional[str] = Field(None, description="GitHub signature", example="sha256=...")
    payload: Dict[str, Any] = Field(..., description="Webhook payload")


class WebhookResponse(BaseModel):
    """
    Schema for webhook response.
    """
    status: str = Field(..., description="Status of the webhook processing", example="success")
    message: str = Field(..., description="Message describing the result", example="Webhook received and processed")
    event_type: str = Field(..., description="GitHub event type", example="push")
    delivery_id: Optional[str] = Field(None, description="GitHub delivery ID", example="72d3162e-cc78-11e3-81ab-4c9367dc0958")
    saved_file: str = Field(..., description="Path to the saved webhook data file", example="data/push_20210101_120000_123.json")
    timestamp: str = Field(..., description="Timestamp of the webhook processing", example="2021-01-01T12:00:00.123456")


class ErrorResponse(BaseModel):
    """
    Schema for error response.
    """
    status: str = Field("error", description="Status of the request", example="error")
    message: str = Field(..., description="Error message", example="Invalid request")
    detail: Optional[str] = Field(None, description="Detailed error information", example="Missing required field: name")
    timestamp: str = Field(..., description="Timestamp of the error", example="2021-01-01T12:00:00.123456")


class HealthResponse(BaseModel):
    """
    Schema for health check response.
    """
    status: str = Field(..., description="Status of the server", example="healthy")
    timestamp: str = Field(..., description="Timestamp of the health check", example="2021-01-01T12:00:00.123456")
    version: str = Field(..., description="Server version", example="1.0.0")
    uptime: float = Field(..., description="Server uptime in seconds", example=3600.0)


class ServerInfoResponse(BaseModel):
    """
    Schema for server information response.
    """
    message: str = Field(..., description="Server status message", example="GitHub Webhook Server is running")
    status: str = Field(..., description="Server status", example="running")
    data_dir: str = Field(..., description="Data directory path", example="/app/data")
    webhook_endpoint: str = Field(..., description="Webhook endpoint", example="/api/v1/webhook")
    version: str = Field(..., description="Server version", example="1.0.0")
    settings: Dict[str, Any] = Field(..., description="Server settings")


class FileInfo(BaseModel):
    """
    Schema for file information.
    """
    filename: str = Field(..., description="Filename", example="push_20210101_120000_123.json")
    size: int = Field(..., description="File size in bytes", example=1024)
    created: str = Field(..., description="File creation timestamp", example="2021-01-01T12:00:00.123456")
    modified: str = Field(..., description="File modification timestamp", example="2021-01-01T12:00:00.123456")


class FileListResponse(BaseModel):
    """
    Schema for file list response.
    """
    total_files: int = Field(..., description="Total number of files", example=10)
    files: List[FileInfo] = Field(..., description="List of files")