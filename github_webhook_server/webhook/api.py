"""
API endpoints for the webhook server.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.orm import Session

from webhook import schemas
from webhook.config import API_VERSION, DATA_DIR, get_settings
from webhook.models import Client, MessageConsumption, get_db
from webhook.utils import (
    message_matches_client_interest,
    save_webhook_data,
    verify_signature,
)

# Create API routers
webhook_router = APIRouter(tags=["webhook"])
client_router = APIRouter(prefix="/clients", tags=["clients"])
system_router = APIRouter(tags=["system"])

# Server start time for uptime calculation
SERVER_START_TIME = time.time()


@webhook_router.post("/webhook", response_model=schemas.WebhookResponse)
async def receive_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
) -> JSONResponse:
    """
    Receive and process GitHub webhook events.
    
    This endpoint receives webhook events from GitHub, verifies the signature,
    and stores the event data for later processing.
    
    Args:
        request: The FastAPI request object
        x_github_event: The GitHub event type header
        x_hub_signature_256: The GitHub signature header
        x_github_delivery: The GitHub delivery ID header
        
    Returns:
        JSONResponse: A response indicating the status of the webhook processing
        
    Raises:
        HTTPException: If the signature verification fails or if there's an error processing the webhook
    """
    try:
        # 요청 본문 읽기
        payload_body = await request.body()

        # 서명 검증
        if not verify_signature(payload_body, x_hub_signature_256 or ""):
            logger.error("Webhook 서명 검증 실패")
            raise HTTPException(status_code=403, detail="서명 검증 실패")

        # JSON 파싱
        try:
            payload = json.loads(payload_body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 에러: {e}")
            raise HTTPException(status_code=400, detail="유효하지 않은 JSON 형식")

        # 이벤트 타입 확인
        event_type = x_github_event or "unknown"

        logger.info(
            f"GitHub Webhook 수신: {event_type} (Delivery: {x_github_delivery})"
        )

        # 데이터 저장
        saved_file, org_name, repo_name = save_webhook_data(payload, event_type)

        # 응답
        response_data = {
            "status": "success",
            "message": "Webhook 수신 완료",
            "event_type": event_type,
            "delivery_id": x_github_delivery,
            "saved_file": saved_file,
            "timestamp": datetime.now().isoformat(),
        }

        return JSONResponse(content=response_data, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"내부 서버 오류: {str(e)}")


@client_router.post("", response_model=schemas.ClientResponse)
async def create_client(
    client_data: schemas.ClientCreate, db: Session = Depends(get_db)
) -> schemas.ClientResponse:
    """
    Register a new client or return an existing client.
    
    Args:
        client_data: The client data
        db: The database session
        
    Returns:
        ClientResponse: The client response
    """
    # 이름 중복 체크
    existing_client = db.query(Client).filter(Client.name == client_data.name).first()
    if existing_client:
        # 이미 존재하는 클라이언트면 기존 클라이언트 정보 반환
        logger.info(
            f"기존 클라이언트를 반환합니다: {existing_client.name} (ID: {existing_client.id})"
        )
        return schemas.ClientResponse(
            id=existing_client.id,
            name=existing_client.name,
            description=existing_client.description,
            interested_orgs=existing_client.get_interested_orgs(),
            interested_repos=existing_client.get_interested_repos(),
            created_at=existing_client.created_at,
            last_poll_at=existing_client.last_poll_at,
        )

    # 새 클라이언트 생성
    new_client = Client(name=client_data.name, description=client_data.description)

    if client_data.interested_orgs:
        new_client.set_interested_orgs(client_data.interested_orgs)

    if client_data.interested_repos:
        new_client.set_interested_repos(client_data.interested_repos)

    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    # 응답용 데이터 구성
    response_data = schemas.ClientResponse(
        id=new_client.id,
        name=new_client.name,
        description=new_client.description,
        interested_orgs=new_client.get_interested_orgs(),
        interested_repos=new_client.get_interested_repos(),
        created_at=new_client.created_at,
        last_poll_at=new_client.last_poll_at,
    )

    logger.info(
        f"새 클라이언트가 등록되었습니다: {new_client.name} (ID: {new_client.id})"
    )
    return response_data


@client_router.get("", response_model=List[schemas.ClientResponse])
async def list_clients(db: Session = Depends(get_db)) -> List[schemas.ClientResponse]:
    """
    List all clients.
    
    Args:
        db: The database session
        
    Returns:
        List[ClientResponse]: The list of clients
    """
    clients = db.query(Client).all()

    return [
        schemas.ClientResponse(
            id=client.id,
            name=client.name,
            description=client.description,
            interested_orgs=client.get_interested_orgs(),
            interested_repos=client.get_interested_repos(),
            created_at=client.created_at,
            last_poll_at=client.last_poll_at,
        )
        for client in clients
    ]


@client_router.get("/{client_id}", response_model=schemas.ClientResponse)
async def get_client(client_id: int, db: Session = Depends(get_db)) -> schemas.ClientResponse:
    """
    Get a specific client.
    
    Args:
        client_id: The client ID
        db: The database session
        
    Returns:
        ClientResponse: The client response
        
    Raises:
        HTTPException: If the client is not found
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="클라이언트를 찾을 수 없습니다")

    return schemas.ClientResponse(
        id=client.id,
        name=client.name,
        description=client.description,
        interested_orgs=client.get_interested_orgs(),
        interested_repos=client.get_interested_repos(),
        created_at=client.created_at,
        last_poll_at=client.last_poll_at,
    )


@client_router.get("/poll/{client_id}", response_model=schemas.PollResponse)
async def poll_messages(client_id: int, db: Session = Depends(get_db)) -> schemas.PollResponse:
    """
    Poll for new messages for a specific client.
    
    Args:
        client_id: The client ID
        db: The database session
        
    Returns:
        PollResponse: The poll response
        
    Raises:
        HTTPException: If the client is not found
    """
    # 클라이언트 존재 확인
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="클라이언트를 찾을 수 없습니다")

    # 이미 소비한 메시지 목록 가져오기
    consumed_files = set()
    consumed_messages = (
        db.query(MessageConsumption)
        .filter(MessageConsumption.client_id == client_id)
        .all()
    )

    for msg in consumed_messages:
        consumed_files.add(msg.message_file)

    # 새로운 메시지 찾기
    new_messages = []

    for file_path in DATA_DIR.glob("*.json"):
        filename = file_path.name

        # 이미 소비한 메시지는 건너뛰기
        if filename in consumed_files:
            continue

        try:
            # 파일 읽기
            with open(file_path, "r", encoding="utf-8") as f:
                webhook_data = json.load(f)

            # 클라이언트 관심사와 매칭 확인
            if message_matches_client_interest(
                webhook_data, 
                client.get_interested_orgs(), 
                client.get_interested_repos()
            ):
                new_messages.append(
                    {
                        "filename": filename,
                        "timestamp": webhook_data.get("timestamp"),
                        "event_type": webhook_data.get("event_type"),
                        "org_name": webhook_data.get("org_name"),
                        "repo_name": webhook_data.get("repo_name"),
                        "payload": webhook_data.get("payload"),
                    }
                )

                # 소비 이력 기록
                consumption = MessageConsumption(
                    client_id=client_id,
                    message_file=filename,
                    event_type=webhook_data.get("event_type", "unknown"),
                    org_name=webhook_data.get("org_name"),
                    repo_name=webhook_data.get("repo_name"),
                )
                db.add(consumption)

        except Exception as e:
            logger.error(f"파일 읽기 오류 ({filename}): {e}")
            continue

    # 클라이언트의 마지막 poll 시간 업데이트
    now = datetime.now()
    db.query(Client).filter(Client.id == client_id).update({"last_poll_at": now})
    db.commit()

    logger.info(
        f"클라이언트 {client.name} (ID: {client_id})가 {len(new_messages)}개의 새 메시지를 polling했습니다"
    )

    return schemas.PollResponse(
        client_id=client_id,
        messages=new_messages,
        total_new_messages=len(new_messages),
        poll_timestamp=now,
    )


@system_router.get("/", response_model=schemas.ServerInfoResponse)
async def root() -> schemas.ServerInfoResponse:
    """
    Get server information.
    
    Returns:
        ServerInfoResponse: The server information
    """
    settings = get_settings()
    return schemas.ServerInfoResponse(
        message="GitHub Webhook Server가 실행 중입니다",
        status="running",
        data_dir=settings["data_dir"],
        webhook_endpoint="/webhook",
        version=API_VERSION,
        settings=settings,
    )


@system_router.get("/health", response_model=schemas.HealthResponse)
async def health_check() -> schemas.HealthResponse:
    """
    Check server health.
    
    Returns:
        HealthResponse: The health check response
    """
    return schemas.HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=API_VERSION,
        uptime=time.time() - SERVER_START_TIME,
    )


@system_router.get("/files", response_model=schemas.FileListResponse)
async def list_saved_files() -> schemas.FileListResponse:
    """
    List saved webhook files.
    
    Returns:
        FileListResponse: The file list response
    """
    files = []
    for file_path in DATA_DIR.glob("*.json"):
        stat = file_path.stat()
        files.append(
            schemas.FileInfo(
                filename=file_path.name,
                size=stat.st_size,
                created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            )
        )

    return schemas.FileListResponse(
        total_files=len(files),
        files=sorted(files, key=lambda x: x.created, reverse=True),
    )