#!/usr/bin/env python3
"""
Deep Research MCP Server using DuckDuckGo
복잡한 주제에 대한 심층 리서치를 수행하고 종합적인 결과를 제공하는 도구입니다.
Perplexity와 유사하게 여러 검색 결과를 종합하여 포괄적인 답변을 생성합니다.
"""

import os
import json
import re
import html
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set

import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# Create MCP Server
app = FastMCP(
    title="Deep Research Server",
    description="A server for comprehensive research using DuckDuckGo",
    version="1.0.0",
)

TRANSPORT = "stdio"

# DuckDuckGo 설정
BASE_URL = "https://duckduckgo.com"
SEARCH_URL = "https://duckduckgo.com/html"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 검색 설정
MAX_SUBQUERIES = 5  # 최대 하위 쿼리 수
MAX_RESULTS_PER_QUERY = 10  # 쿼리당 최대 결과 수
SEARCH_DELAY = 1  # 검색 간 지연 시간(초)


@dataclass
class SearchResult:
    """검색 결과를 담는 데이터 클래스"""
    title: str
    url: str
    description: str
    source: str
    timestamp: str
    relevance_score: float = 0.0
    content: str = ""
    
    def get_id(self) -> str:
        """결과의 고유 ID를 생성합니다."""
        return hashlib.md5(f"{self.url}".encode()).hexdigest()


@dataclass
class ResearchTopic:
    """연구 주제를 담는 데이터 클래스"""
    main_query: str
    subqueries: List[str] = field(default_factory=list)
    results: Dict[str, List[SearchResult]] = field(default_factory=dict)
    sources: Set[str] = field(default_factory=set)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DuckDuckGoService:
    """DuckDuckGo 검색 서비스 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://duckduckgo.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-GPC": "1",
        })
    
    def search(self, query: str, region: str = "kr-kr", safe_search: str = "moderate", time_period: str = None) -> List[SearchResult]:
        """DuckDuckGo에서 검색을 수행합니다."""
        try:
            # 검색 파라미터 설정
            params = {
                "q": query,
                "kl": region,  # 지역 설정
                "kp": self._get_safe_search_param(safe_search),  # 세이프서치 설정
                "kaf": "1",  # 자동 완성 비활성화
                "kac": "-1",  # 자동 제안 비활성화
            }
            
            # 시간 필터 추가
            if time_period:
                params["df"] = self._get_time_period_param(time_period)
            
            # 검색 요청
            response = self.session.get(SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            # 검색 결과 추출
            for result in soup.select(".result"):
                try:
                    title_elem = result.select_one(".result__title")
                    url_elem = result.select_one(".result__url")
                    desc_elem = result.select_one(".result__snippet")
                    
                    if title_elem and url_elem:
                        title = title_elem.get_text(strip=True)
                        url = url_elem.get_text(strip=True)
                        if not url.startswith(("http://", "https://")):
                            url = "https://" + url
                        
                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        source = url.split("//")[-1].split("/")[0]
                        
                        # 기본 관련성 점수 계산 (제목과 설명의 길이 기반)
                        relevance_score = min(len(title) * 0.2 + len(description) * 0.1, 10.0)
                        
                        results.append(SearchResult(
                            title=title,
                            url=url,
                            description=description,
                            source=source,
                            timestamp=datetime.now().isoformat(),
                            relevance_score=relevance_score
                        ))
                except Exception:
                    continue
            
            return results
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []
    
    def _get_safe_search_param(self, safe_search: str) -> str:
        """세이프서치 파라미터를 변환합니다."""
        if safe_search.lower() == "strict":
            return "1"  # 엄격
        elif safe_search.lower() == "off":
            return "-2"  # 끄기
        else:
            return "0"  # 보통 (기본값)
    
    def _get_time_period_param(self, time_period: str) -> str:
        """시간 필터 파라미터를 변환합니다."""
        time_map = {
            "day": "d",
            "week": "w",
            "month": "m",
            "year": "y"
        }
        return time_map.get(time_period.lower(), "")
    
    def fetch_content(self, url: str, max_length: int = 5000) -> str:
        """URL에서 콘텐츠를 가져옵니다."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 불필요한 요소 제거
            for tag in soup.select("script, style, nav, footer, header, aside"):
                tag.decompose()
            
            # 본문 추출 시도
            content = ""
            main_content = soup.select_one("main, article, #content, .content, .article, .post")
            
            if main_content:
                content = main_content.get_text(separator=" ", strip=True)
            else:
                # 본문 요소를 찾지 못한 경우 body 전체 사용
                content = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
            
            # 공백 정리
            content = re.sub(r'\s+', ' ', content).strip()
            
            # 길이 제한
            if len(content) > max_length:
                content = content[:max_length] + "..."
            
            return content
        except Exception as e:
            print(f"Content fetch error for {url}: {str(e)}")
            return ""


class ResearchService:
    """심층 연구 서비스 클래스"""
    
    def __init__(self):
        self.search_service = DuckDuckGoService()
        self.research_cache = {}  # 연구 결과 캐시
    
    def generate_subqueries(self, main_query: str, max_subqueries: int = MAX_SUBQUERIES) -> List[str]:
        """주 쿼리에서 하위 쿼리를 생성합니다."""
        # 기본 하위 쿼리 패턴
        patterns = [
            f"{main_query} 정의",
            f"{main_query} 역사",
            f"{main_query} 장점",
            f"{main_query} 단점",
            f"{main_query} 사례",
            f"{main_query} 최신 동향",
            f"{main_query} 통계",
            f"{main_query} 비교",
            f"{main_query} 미래",
            f"{main_query} 영향"
        ]
        
        # 쿼리 유형에 따라 다른 패턴 추가
        if "vs" in main_query or "비교" in main_query:
            parts = main_query.split("vs")
            if len(parts) == 2:
                a, b = parts[0].strip(), parts[1].strip()
                patterns.extend([
                    f"{a} 장점",
                    f"{b} 장점",
                    f"{a} vs {b} 차이점"
                ])
        
        elif "방법" in main_query or "하는 법" in main_query or "how" in main_query.lower():
            patterns.extend([
                f"{main_query} 단계별",
                f"{main_query} 팁",
                f"{main_query} 실수",
                f"{main_query} 도구"
            ])
        
        elif "이유" in main_query or "why" in main_query.lower():
            patterns.extend([
                f"{main_query} 원인",
                f"{main_query} 배경",
                f"{main_query} 분석",
                f"{main_query} 전문가 의견"
            ])
        
        # 중복 제거 및 최대 개수 제한
        unique_subqueries = list(dict.fromkeys(patterns))
        return unique_subqueries[:max_subqueries]
    
    def conduct_research(self, query: str, region: str = "kr-kr", time_period: str = None) -> ResearchTopic:
        """주제에 대한 심층 연구를 수행합니다."""
        # 캐시 확인
        cache_key = f"{query}_{region}_{time_period}"
        if cache_key in self.research_cache:
            return self.research_cache[cache_key]
        
        # 새 연구 주제 생성
        research = ResearchTopic(main_query=query)
        
        # 하위 쿼리 생성
        research.subqueries = self.generate_subqueries(query)
        
        # 메인 쿼리 검색
        main_results = self.search_service.search(query, region, "moderate", time_period)
        research.results[query] = main_results
        
        # 하위 쿼리 검색
        for subquery in research.subqueries:
            # 검색 간 지연
            time.sleep(SEARCH_DELAY)
            
            results = self.search_service.search(subquery, region, "moderate", time_period)
            research.results[subquery] = results
            
            # 소스 추적
            for result in results:
                research.sources.add(result.source)
        
        # 상위 결과에 대한 콘텐츠 가져오기
        self._fetch_top_content(research)
        
        # 캐시에 저장
        self.research_cache[cache_key] = research
        
        return research
    
    def _fetch_top_content(self, research: ResearchTopic, top_n: int = 3):
        """상위 결과에 대한 콘텐츠를 가져옵니다."""
        # 모든 결과 수집
        all_results = []
        for query_results in research.results.values():
            all_results.extend(query_results)
        
        # 중복 제거 (URL 기준)
        unique_results = {}
        for result in all_results:
            result_id = result.get_id()
            if result_id not in unique_results or result.relevance_score > unique_results[result_id].relevance_score:
                unique_results[result_id] = result
        
        # 관련성 점수로 정렬
        sorted_results = sorted(unique_results.values(), key=lambda x: x.relevance_score, reverse=True)
        
        # 상위 결과에 대한 콘텐츠 가져오기
        for result in sorted_results[:top_n]:
            if not result.content:  # 아직 콘텐츠가 없는 경우에만
                result.content = self.search_service.fetch_content(result.url)
                # 검색 간 지연
                time.sleep(SEARCH_DELAY)
    
    def synthesize_research(self, research: ResearchTopic) -> Dict[str, Any]:
        """연구 결과를 종합하여 구조화된 응답을 생성합니다."""
        # 모든 결과 수집 및 중복 제거
        all_results = []
        for query_results in research.results.values():
            all_results.extend(query_results)
        
        unique_results = {}
        for result in all_results:
            result_id = result.get_id()
            if result_id not in unique_results or result.relevance_score > unique_results[result_id].relevance_score:
                unique_results[result_id] = result
        
        # 관련성 점수로 정렬
        sorted_results = sorted(unique_results.values(), key=lambda x: x.relevance_score, reverse=True)
        
        # 상위 결과 선택
        top_results = sorted_results[:10]
        
        # 쿼리별 주요 결과 구성
        query_insights = {}
        for query, results in research.results.items():
            if results:
                # 상위 3개 결과만 선택
                top_query_results = sorted(results, key=lambda x: x.relevance_score, reverse=True)[:3]
                
                query_insights[query] = {
                    "key_points": [result.description for result in top_query_results if result.description],
                    "sources": [{"title": result.title, "url": result.url, "source": result.source} 
                               for result in top_query_results]
                }
        
        # 종합 결과 구성
        synthesis = {
            "main_query": research.main_query,
            "timestamp": research.timestamp,
            "total_sources": len(research.sources),
            "subqueries_explored": len(research.subqueries),
            "top_results": [
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description,
                    "source": result.source,
                    "content_preview": result.content[:200] + "..." if result.content else ""
                }
                for result in top_results
            ],
            "query_insights": query_insights,
            "sources_list": list(research.sources)
        }
        
        return synthesis


# 전역 서비스 인스턴스
research_service = ResearchService()


@app.tool()
def deep_research(query: str, region: str = "kr-kr", time_period: str = None) -> dict:
    """
    주제에 대한 심층 연구를 수행합니다.
    
    여러 하위 쿼리를 자동으로 생성하고 검색하여 포괄적인 결과를 제공합니다.
    Perplexity와 유사하게 다양한 소스에서 정보를 종합합니다.

    Args:
        query: 연구할 주제 또는 질문
        region: 검색 지역 (예: kr-kr, us-en, wt-wt)
        time_period: 검색 기간 (day, week, month, year)

    Returns:
        dict: 종합적인 연구 결과를 포함한 딕셔너리
    """
    try:
        if not query:
            return {"error": "연구할 주제를 입력해주세요."}
        
        # 심층 연구 수행
        research = research_service.conduct_research(query, region, time_period)
        
        # 연구 결과 종합
        synthesis = research_service.synthesize_research(research)
        
        return {
            "result": synthesis
        }
        
    except Exception as e:
        return {"error": f"연구 중 오류 발생: {str(e)}"}


@app.tool()
def research_with_custom_subqueries(query: str, subqueries: List[str], region: str = "kr-kr") -> dict:
    """
    사용자 정의 하위 쿼리로 심층 연구를 수행합니다.
    
    메인 쿼리와 함께 사용자가 지정한 하위 쿼리들을 검색하여 결과를 종합합니다.

    Args:
        query: 주 연구 주제
        subqueries: 사용자 정의 하위 쿼리 목록
        region: 검색 지역 (예: kr-kr, us-en, wt-wt)

    Returns:
        dict: 종합적인 연구 결과를 포함한 딕셔너리
    """
    try:
        if not query:
            return {"error": "연구할 주제를 입력해주세요."}
        
        if not subqueries or not isinstance(subqueries, list):
            return {"error": "하위 쿼리 목록을 제공해주세요."}
        
        # 새 연구 주제 생성
        research = ResearchTopic(main_query=query)
        research.subqueries = subqueries[:MAX_SUBQUERIES]  # 최대 개수 제한
        
        # 메인 쿼리 검색
        main_results = research_service.search_service.search(query, region)
        research.results[query] = main_results
        
        # 하위 쿼리 검색
        for subquery in research.subqueries:
            # 검색 간 지연
            time.sleep(SEARCH_DELAY)
            
            results = research_service.search_service.search(subquery, region)
            research.results[subquery] = results
            
            # 소스 추적
            for result in results:
                research.sources.add(result.source)
        
        # 상위 결과에 대한 콘텐츠 가져오기
        research_service._fetch_top_content(research)
        
        # 연구 결과 종합
        synthesis = research_service.synthesize_research(research)
        
        return {
            "result": synthesis
        }
        
    except Exception as e:
        return {"error": f"연구 중 오류 발생: {str(e)}"}


@app.tool()
def get_suggested_subqueries(query: str) -> dict:
    """
    주 쿼리에 대한 추천 하위 쿼리를 생성합니다.
    
    심층 연구에 사용할 수 있는 하위 쿼리 목록을 제안합니다.

    Args:
        query: 주 연구 주제

    Returns:
        dict: 추천 하위 쿼리 목록을 포함한 딕셔너리
    """
    try:
        if not query:
            return {"error": "주제를 입력해주세요."}
        
        # 하위 쿼리 생성
        subqueries = research_service.generate_subqueries(query)
        
        return {
            "result": {
                "main_query": query,
                "suggested_subqueries": subqueries,
                "count": len(subqueries)
            }
        }
        
    except Exception as e:
        return {"error": f"하위 쿼리 생성 중 오류 발생: {str(e)}"}


@app.tool()
def get_research_info() -> dict:
    """
    심층 연구 도구 정보를 반환합니다.

    Returns:
        dict: 심층 연구 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Deep Research Tool",
                "description": "DuckDuckGo를 사용한 Perplexity 스타일의 심층 연구 도구",
                "capabilities": [
                    "주제 분해 및 하위 쿼리 생성",
                    "다중 검색 실행",
                    "결과 종합 및 구조화",
                    "소스 추적 및 인용",
                    "콘텐츠 미리보기"
                ],
                "limitations": [
                    "검색 엔진 결과에 의존",
                    "콘텐츠 추출이 모든 웹사이트에서 완벽하게 작동하지 않을 수 있음",
                    "검색 간 지연으로 인한 응답 시간 증가",
                    "검색 결과의 품질은 DuckDuckGo 검색 엔진에 의존"
                ],
                "usage_examples": [
                    "복잡한 주제에 대한 포괄적인 정보 수집",
                    "여러 관점에서 주제 탐색",
                    "최신 트렌드 및 발전 사항 조사",
                    "비교 분석 수행"
                ]
            }
        }
        
    except Exception as e:
        return {"error": f"도구 정보를 가져오는 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    app.run(transport=TRANSPORT)