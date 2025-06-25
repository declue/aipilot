# 🔍 DuckDuckGo Search MCP Server

- FastMCP를 이용한 웹 검색 도구입니다.
- DuckDuckGo 검색 엔진을 사용하여 프라이버시를 보호하면서 검색 결과를 얻을 수 있습니다.

## ✨ 주요 기능

- 🌐 **기본 웹 검색**: 다양한 지역 및 세이프서치 설정으로 웹 검색
- ⏱️ **시간 필터 검색**: 특정 기간 내의 결과만 검색
- 🔤 **검색어 자동 완성**: 검색어 입력 시 추천 검색어 제공
- 🖼️ **이미지 검색**: 이미지 검색 결과 제공
- 🌍 **다국어 지원**: 다양한 지역 및 언어 설정 지원

## 📦 설치

필요한 패키지를 설치합니다:

```bash
pip install fastmcp requests beautifulsoup4 duckduckgo_search
```

## 🚀 사용 방법

### 1. MCP 서버 시작

```bash
python tools/duckduckgo_mcp_tool.py
```

### 2. 사용 가능한 도구들

#### 🌐 기본 웹 검색

```python
result = await mcp_client.call_tool("search_web", {
    "query": "파이썬 프로그래밍",
    "region": "kr-kr",
    "safe_search": "moderate",
    "max_results": 10
})
```

#### ⏱️ 시간 필터 검색

```python
result = await mcp_client.call_tool("search_with_time_filter", {
    "query": "최신 기술 트렌드",
    "time_period": "week",  # day, week, month, year
    "region": "kr-kr",
    "max_results": 10
})
```

#### 🔤 검색어 자동 완성

```python
result = await mcp_client.call_tool("get_search_suggestions", {
    "query": "파이썬 프로그래"
})
```

#### 🖼️ 이미지 검색

```python
result = await mcp_client.call_tool("search_images", {
    "query": "자연 풍경",
    "max_results": 10
})
```

#### ℹ️ 검색 도구 정보

```python
result = await mcp_client.call_tool("get_search_info")
```

## 📊 응답 형식

모든 도구는 다음과 같은 형식으로 응답합니다:

### 성공 시

```json
{
    "result": {
        "query": "검색어",
        "count": 10,
        "results": [
            {
                "title": "결과 제목",
                "url": "https://example.com",
                "description": "결과 설명",
                "source": "example.com"
            },
            ...
        ]
    }
}
```

### 오류 발생 시

```json
{
    "error": "오류 메시지"
}
```

## 🧪 고급 사용 예제

### 여러 지역에서 검색 결과 비교

```python
async def compare_search_results(query):
    regions = ["kr-kr", "us-en", "jp-jp"]
    results = {}
    
    for region in regions:
        response = await mcp_client.call_tool("search_web", {
            "query": query,
            "region": region,
            "max_results": 5
        })
        
        if "result" in response:
            results[region] = response["result"]["results"]
    
    # 결과 비교 및 분석
    common_domains = set()
    for region, region_results in results.items():
        domains = [result["source"] for result in region_results]
        if not common_domains:
            common_domains = set(domains)
        else:
            common_domains = common_domains.intersection(set(domains))
    
    print(f"모든 지역에서 공통으로 나타나는 도메인: {common_domains}")
    return results
```

### 검색어 추천 기반 키워드 확장

```python
async def expand_keywords(seed_keyword):
    keywords = [seed_keyword]
    expanded = set()
    
    for keyword in keywords:
        response = await mcp_client.call_tool("get_search_suggestions", {
            "query": keyword
        })
        
        if "result" in response and "suggestions" in response["result"]:
            suggestions = response["result"]["suggestions"]
            for suggestion in suggestions:
                if suggestion not in expanded and suggestion != keyword:
                    expanded.add(suggestion)
                    if len(expanded) >= 20:  # 최대 20개 키워드로 제한
                        break
    
    return list(expanded)
```

### 최신 뉴스 모니터링

```python
async def monitor_news(topic, interval_hours=24):
    last_check = datetime.now()
    seen_urls = set()
    
    while True:
        current_time = datetime.now()
        hours_passed = (current_time - last_check).total_seconds() / 3600
        
        if hours_passed >= interval_hours:
            response = await mcp_client.call_tool("search_with_time_filter", {
                "query": topic,
                "time_period": "day",
                "max_results": 20
            })
            
            if "result" in response and "results" in response["result"]:
                new_results = []
                for result in response["result"]["results"]:
                    if result["url"] not in seen_urls:
                        new_results.append(result)
                        seen_urls.add(result["url"])
                
                if new_results:
                    print(f"새로운 {topic} 관련 뉴스 {len(new_results)}개 발견:")
                    for i, result in enumerate(new_results, 1):
                        print(f"{i}. {result['title']} - {result['url']}")
            
            last_check = current_time
        
        await asyncio.sleep(3600)  # 1시간마다 체크
```

## 📋 지원되는 지역 설정

DuckDuckGo 검색은 다음과 같은 지역 설정을 지원합니다:

| 코드 | 지역 |
|------|------|
| wt-wt | 전 세계 (기본값) |
| kr-kr | 대한민국 |
| us-en | 미국 (영어) |
| uk-en | 영국 (영어) |
| jp-jp | 일본 |
| cn-zh | 중국 |
| de-de | 독일 |
| fr-fr | 프랑스 |
| es-es | 스페인 |
| it-it | 이탈리아 |
| ru-ru | 러시아 |
| ca-en | 캐나다 (영어) |
| ca-fr | 캐나다 (프랑스어) |
| au-en | 호주 |

## 🛡️ 보안 및 프라이버시

DuckDuckGo는 사용자의 프라이버시를 보호하는 검색 엔진으로, 다음과 같은 특징이 있습니다:

- 사용자 추적 없음
- 검색 기록 저장 없음
- 개인화된 검색 결과 없음 (필터 버블 방지)
- 광고 추적 차단

이 MCP 도구는 DuckDuckGo의 HTML 검색 인터페이스를 사용하여 검색 결과를 가져오므로, DuckDuckGo의 프라이버시 보호 기능을 그대로 활용할 수 있습니다.
