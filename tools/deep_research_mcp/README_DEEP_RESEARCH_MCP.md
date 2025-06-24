# 🔍 Deep Research MCP Server

FastMCP를 이용한 심층 연구 도구입니다. DuckDuckGo 검색 엔진을 사용하여 Perplexity와 유사한 방식으로 복잡한 주제에 대한 포괄적인 연구를 수행합니다.

## ✨ 주요 기능

- 🧠 **주제 분해**: 복잡한 주제를 여러 하위 쿼리로 자동 분해
- 🔄 **다중 검색 실행**: 여러 관련 쿼리를 동시에 검색하여 포괄적인 정보 수집
- 📊 **정보 종합**: 다양한 소스에서 수집한 정보를 구조화된 형태로 종합
- 📝 **소스 추적**: 모든 정보의 출처를 명확하게 추적하고 인용
- 📄 **콘텐츠 미리보기**: 주요 결과의 콘텐츠를 직접 추출하여 제공

## 📦 설치

필요한 패키지를 설치합니다:

```bash
pip install fastmcp requests beautifulsoup4
```

## 🚀 사용 방법

### 1. MCP 서버 시작

```bash
python tools/deep_research_mcp.py
```

### 2. 사용 가능한 도구들

#### 🔍 심층 연구 수행

```python
result = await mcp_client.call_tool("deep_research", {
    "query": "인공지능의 윤리적 문제",
    "region": "kr-kr",
    "time_period": "month"  # 선택 사항: day, week, month, year
})
```

#### 🧩 사용자 정의 하위 쿼리로 연구

```python
result = await mcp_client.call_tool("research_with_custom_subqueries", {
    "query": "기후 변화 대응 방안",
    "subqueries": [
        "기후 변화 대응 국제 협약",
        "기후 변화 대응 기술",
        "기후 변화 대응 정책",
        "기후 변화 대응 기업 사례",
        "기후 변화 대응 개인 실천 방안"
    ],
    "region": "kr-kr"
})
```

#### 🔤 추천 하위 쿼리 생성

```python
result = await mcp_client.call_tool("get_suggested_subqueries", {
    "query": "블록체인 기술의 미래"
})
```

#### ℹ️ 연구 도구 정보

```python
result = await mcp_client.call_tool("get_research_info")
```

## 📊 응답 형식

심층 연구 도구는 다음과 같은 형식으로 응답합니다:

### 성공 시:

```json
{
    "result": {
        "main_query": "인공지능의 윤리적 문제",
        "timestamp": "2023-06-24T10:30:00.123456",
        "total_sources": 15,
        "subqueries_explored": 5,
        "top_results": [
            {
                "title": "인공지능 윤리의 주요 쟁점과 과제",
                "url": "https://example.com/ai-ethics",
                "description": "인공지능 기술 발전에 따른 윤리적 문제와 해결 방안에 대한 분석",
                "source": "example.com",
                "content_preview": "인공지능 기술이 발전함에 따라 프라이버시, 편향성, 투명성, 책임성 등 다양한 윤리적 문제가 제기되고 있다..."
            },
            ...
        ],
        "query_insights": {
            "인공지능의 윤리적 문제": {
                "key_points": ["프라이버시 침해 우려", "알고리즘 편향성", "의사결정 투명성 부족"],
                "sources": [...]
            },
            "인공지능 윤리 가이드라인": {
                "key_points": ["EU AI 규제 프레임워크", "IEEE 윤리적 설계 원칙", "OECD AI 원칙"],
                "sources": [...]
            },
            ...
        },
        "sources_list": ["example.com", "research.org", "university.edu", ...]
    }
}
```

### 오류 발생 시:

```json
{
    "error": "오류 메시지"
}
```

## 🧪 고급 사용 예제

### 다양한 관점에서 주제 탐색

```python
async def explore_topic_from_multiple_perspectives(topic):
    # 기본 연구 수행
    base_research = await mcp_client.call_tool("deep_research", {
        "query": topic
    })
    
    # 추천 하위 쿼리 가져오기
    subqueries_response = await mcp_client.call_tool("get_suggested_subqueries", {
        "query": topic
    })
    
    if "result" in subqueries_response:
        suggested_subqueries = subqueries_response["result"]["suggested_subqueries"]
        
        # 찬성/반대 관점 추가
        perspective_subqueries = [
            f"{topic} 찬성 의견",
            f"{topic} 반대 의견",
            f"{topic} 대안",
            f"{topic} 비판",
            f"{topic} 사례 연구"
        ]
        
        # 사용자 정의 하위 쿼리로 추가 연구
        custom_research = await mcp_client.call_tool("research_with_custom_subqueries", {
            "query": topic,
            "subqueries": perspective_subqueries
        })
        
        # 결과 종합
        return {
            "base_research": base_research["result"] if "result" in base_research else {},
            "perspective_research": custom_research["result"] if "result" in custom_research else {},
            "all_subqueries": suggested_subqueries + perspective_subqueries
        }
    
    return base_research
```

### 시간에 따른 주제 변화 분석

```python
async def analyze_topic_over_time(topic):
    time_periods = ["day", "week", "month", "year"]
    results = {}
    
    for period in time_periods:
        research = await mcp_client.call_tool("deep_research", {
            "query": topic,
            "time_period": period
        })
        
        if "result" in research:
            results[period] = {
                "top_sources": research["result"]["sources_list"][:5],
                "top_results": [r["title"] for r in research["result"]["top_results"][:3]]
            }
    
    # 시간에 따른 변화 분석
    analysis = {
        "topic": topic,
        "time_analysis": results,
        "changing_trends": compare_results_over_time(results)  # 사용자 정의 분석 함수
    }
    
    return analysis
```

### 비교 연구 수행

```python
async def comparative_research(topic_a, topic_b):
    # 두 주제에 대한 개별 연구
    research_a = await mcp_client.call_tool("deep_research", {"query": topic_a})
    research_b = await mcp_client.call_tool("deep_research", {"query": topic_b})
    
    # 비교 연구
    comparison_query = f"{topic_a} vs {topic_b}"
    comparison_research = await mcp_client.call_tool("deep_research", {"query": comparison_query})
    
    # 결과 종합
    if "result" in research_a and "result" in research_b and "result" in comparison_research:
        return {
            "topic_a": {
                "query": topic_a,
                "key_points": extract_key_points(research_a["result"]),
                "sources": research_a["result"]["sources_list"][:5]
            },
            "topic_b": {
                "query": topic_b,
                "key_points": extract_key_points(research_b["result"]),
                "sources": research_b["result"]["sources_list"][:5]
            },
            "comparison": {
                "query": comparison_query,
                "key_points": extract_key_points(comparison_research["result"]),
                "sources": comparison_research["result"]["sources_list"][:5]
            }
        }
    
    return {"error": "비교 연구 중 오류가 발생했습니다."}
```

## 📋 작동 원리

Deep Research MCP 서버는 다음과 같은 단계로 작동합니다:

1. **주제 분해**: 주 쿼리를 여러 하위 쿼리로 분해합니다.
2. **다중 검색**: 주 쿼리와 모든 하위 쿼리에 대해 DuckDuckGo 검색을 수행합니다.
3. **콘텐츠 추출**: 상위 검색 결과에서 웹 콘텐츠를 직접 추출합니다.
4. **결과 종합**: 모든 검색 결과를 종합하여 구조화된 응답을 생성합니다.
5. **소스 추적**: 모든 정보의 출처를 명확하게 기록합니다.

## 🛡️ 제한 사항

- 검색 엔진 결과에 의존하므로 검색 품질에 영향을 받습니다.
- 웹 콘텐츠 추출이 모든 웹사이트에서 완벽하게 작동하지 않을 수 있습니다.
- 검색 간 지연 시간으로 인해 응답 시간이 길어질 수 있습니다.
- 현재 텍스트 기반 검색만 지원하며 이미지나 비디오 분석은 지원하지 않습니다.

## 🤝 기여

1. 이 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🔗 관련 링크

- [FastMCP](https://github.com/jlowin/fastmcp)
- [DuckDuckGo](https://duckduckgo.com/)
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)
- [Requests](https://requests.readthedocs.io/)