import json
from datetime import datetime
from typing import Any, Generator, List

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Client(Base):  # type: ignore
    """클라이언트 정보"""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    interested_orgs = Column(Text, nullable=True)  # JSON 형태로 저장
    interested_repos = Column(Text, nullable=True)  # JSON 형태로 저장
    created_at = Column(DateTime, default=datetime.now)
    last_poll_at = Column(DateTime, nullable=True)

    # 관계
    consumed_messages = relationship("MessageConsumption", back_populates="client")

    def get_interested_orgs(self) -> List[str]:
        """관심 있는 조직 목록 반환"""
        if not self.interested_orgs:
            return []
        return json.loads(str(self.interested_orgs))  # type: ignore

    def set_interested_orgs(self, orgs: list) -> None:
        """관심 있는 조직 목록 설정"""
        self.interested_orgs = json.dumps(orgs) if orgs else None  # type: ignore

    def get_interested_repos(self) -> List[str]:
        """관심 있는 저장소 목록 반환"""
        if not self.interested_repos:
            return []
        return json.loads(str(self.interested_repos))  # type: ignore

    def set_interested_repos(self, repos: list) -> None:
        """관심 있는 저장소 목록 설정"""
        self.interested_repos = json.dumps(repos) if repos else None  # type: ignore


class MessageConsumption(Base):  # type: ignore
    """메시지 소비 이력"""

    __tablename__ = "message_consumptions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    message_file = Column(String(255), nullable=False)  # 파일명
    event_type = Column(String(50), nullable=False)
    org_name = Column(String(100), nullable=True)
    repo_name = Column(String(100), nullable=True)
    consumed_at = Column(DateTime, default=datetime.now)

    # 관계
    client = relationship("Client", back_populates="consumed_messages")


# 데이터베이스 설정
DATABASE_URL = "sqlite:///./webhook_clients.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """테이블 생성"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Any, None, None]:
    """데이터베이스 세션 가져오기"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()