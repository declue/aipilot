import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from webhook.models import Client, MessageConsumption, create_tables, get_db

app = FastAPI(title="GitHub Webhook Server", version="1.0.0")

# 환경변수에서 GitHub webhook secret 가져오기
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# 데이터 저장 폴더 설정
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# 데이터베이스 테이블 생성
create_tables()


# Pydantic 모델들
class ClientCreate(BaseModel):
    name: str
    description: Optional[str] = None
    interested_orgs: Optional[List[str]] = None
    interested_repos: Optional[List[str]] = None


class ClientResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    interested_orgs: List[str]
    interested_repos: List[str]
    created_at: datetime
    last_poll_at: Optional[datetime]
    
    @classmethod
    def from_client(cls, client: Client) -> 'ClientResponse':
        return cls(
            id=client.id,  # type: ignore
            name=client.name,  # type: ignore
            description=client.description,  # type: ignore
            interested_orgs=client.get_interested_orgs(),
            interested_repos=client.get_interested_repos(),
            created_at=client.created_at,  # type: ignore
            last_poll_at=client.last_poll_at  # type: ignore
        )


class PollResponse(BaseModel):
    client_id: int
    messages: List[Dict[str, Any]]
    total_new_messages: int
    poll_timestamp: datetime


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """GitHub webhook 서명 검증"""
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning(
            "GITHUB_WEBHOOK_SECRET이 설정되지 않았습니다. 서명 검증을 건너뜁니다."
        )
        return True

    if not signature_header:
        return False

    hash_object = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


def extract_org_repo_info(
    payload: Dict[str, Any],
) -> tuple[Optional[str], Optional[str]]:
    """Payload에서 organization과 repository 정보 추출"""
    org_name = None
    repo_name = None

    # Repository 정보 추출
    if "repository" in payload:
        repo_info = payload["repository"]
        repo_name = repo_info.get("full_name") or repo_info.get("name")

        # Organization 정보 추출
        if "owner" in repo_info:
            owner = repo_info["owner"]
            if owner.get("type") == "Organization":
                org_name = owner.get("login")

    # Organization 직접 추출 (organization 이벤트의 경우)
    if "organization" in payload:
        org_name = payload["organization"].get("login")

    return org_name, repo_name


def save_webhook_data(
    payload: Dict[str, Any], event_type: str
) -> tuple[str, Optional[str], Optional[str]]:
    """Webhook 데이터를 파일로 저장하고 org/repo 정보 반환"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초까지

    # 파일명 생성 (이벤트 타입과 타임스탬프 포함)
    filename = f"{event_type}_{timestamp}.json"
    filepath = DATA_DIR / filename

    # org/repo 정보 추출
    org_name, repo_name = extract_org_repo_info(payload)

    # 저장할 데이터 구성
    webhook_data = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "org_name": org_name,
        "repo_name": repo_name,
        "payload": payload,
    }

    # JSON 파일로 저장
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(webhook_data, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Webhook 데이터가 저장되었습니다: {filepath} (org: {org_name}, repo: {repo_name})"
    )
    return str(filepath), org_name, repo_name


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
) -> JSONResponse:
    """GitHub Webhook 수신 엔드포인트"""
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
        raise HTTPException(status_code=500, detail="내부 서버 오류")


@app.get("/")
async def root() -> Dict[str, Any]:
    """서버 상태 확인"""
    return {
        "message": "GitHub Webhook Server가 실행 중입니다",
        "status": "running",
        "data_dir": str(DATA_DIR.absolute()),
        "webhook_endpoint": "/webhook",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/files")
async def list_saved_files() -> Dict[str, Any]:
    """저장된 webhook 파일 목록 조회"""
    files = []
    for file_path in DATA_DIR.glob("*.json"):
        stat = file_path.stat()
        files.append(
            {
                "filename": file_path.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    return {
        "total_files": len(files),
        "files": sorted(files, key=lambda x: x["created"], reverse=True),
    }


# 클라이언트 관리 API
@app.post("/clients", response_model=ClientResponse)
async def create_client(client_data: ClientCreate, db: Session = Depends(get_db)) -> ClientResponse:
    """새 클라이언트 등록 또는 기존 클라이언트 반환"""
    # 이름 중복 체크
    existing_client = db.query(Client).filter(Client.name == client_data.name).first()
    if existing_client:
        # 이미 존재하는 클라이언트면 기존 클라이언트 정보 반환
        logger.info(
            f"기존 클라이언트를 반환합니다: {existing_client.name} (ID: {existing_client.id})"
        )
        return ClientResponse.from_client(existing_client)

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
    response_data = ClientResponse.from_client(new_client)

    logger.info(
        f"새 클라이언트가 등록되었습니다: {new_client.name} (ID: {new_client.id})"
    )
    return response_data


@app.get("/clients", response_model=List[ClientResponse])
async def list_clients(db: Session = Depends(get_db)) -> List[ClientResponse]:
    """클라이언트 목록 조회"""
    clients = db.query(Client).all()

    return [ClientResponse.from_client(client) for client in clients]


@app.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientResponse:
    """특정 클라이언트 정보 조회"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="클라이언트를 찾을 수 없습니다")

    return ClientResponse.from_client(client)


def message_matches_client_interest(
    webhook_data: Dict[str, Any], client: Client
) -> bool:
    """메시지가 클라이언트의 관심사와 일치하는지 확인"""
    org_name = webhook_data.get("org_name")
    repo_name = webhook_data.get("repo_name")

    interested_orgs = client.get_interested_orgs()
    interested_repos = client.get_interested_repos()

    # 관심 있는 조직이나 저장소가 설정되지 않았다면 모든 메시지에 관심
    if not interested_orgs and not interested_repos:
        return True

    # 조직 매칭
    if org_name and interested_orgs:
        if org_name in interested_orgs:
            return True

    # 저장소 매칭 (full_name 또는 repository name)
    if repo_name and interested_repos:
        if repo_name in interested_repos:
            return True
        # full_name에서 repository name만 추출해서 비교
        if "/" in repo_name:
            simple_repo_name = repo_name.split("/")[-1]
            if simple_repo_name in interested_repos:
                return True

    return False


@app.get("/poll/{client_id}", response_model=PollResponse)
async def poll_messages(client_id: int, db: Session = Depends(get_db)) -> PollResponse:
    """클라이언트가 새로운 메시지를 polling"""
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
            if message_matches_client_interest(webhook_data, client):
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

    return PollResponse(
        client_id=client_id,
        messages=new_messages,
        total_new_messages=len(new_messages),
        poll_timestamp=datetime.now(),
    )


if __name__ == "__main__":
    # 로깅 설정
    logger.add("webhook_server.log", rotation="10 MB", retention="7 days")

    # 서버 시작
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
