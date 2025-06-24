#!/usr/bin/env python3
"""
Browser Control MCP Server
웹 브라우저를 제어하고 검색, 클릭 이벤트 등을 수행할 수 있는 도구들을 제공합니다.
LLM Agent에서 활용하기 위한 브라우저 제어 기능을 구현합니다.
"""

import asyncio
import base64
import io
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastmcp import FastMCP
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    ElementNotInteractableException,
    StaleElementReferenceException
)

# MCP 서버 초기화
mcp = FastMCP("Browser Control")

# 브라우저 인스턴스 저장
browser = None
wait = None

# 기본 설정
DEFAULT_TIMEOUT = 10  # 초
DEFAULT_WAIT_TIME = 2  # 초
DEFAULT_SEARCH_ENGINE = "https://www.google.com"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class BrowserElement:
    """브라우저 요소 정보를 담는 데이터 클래스"""
    tag: str
    text: str
    attributes: Dict[str, str]
    location: Dict[str, int]
    is_displayed: bool
    is_enabled: bool
    element_id: str


def get_browser() -> webdriver.Chrome:
    """브라우저 인스턴스를 가져옵니다."""
    global browser, wait
    
    if browser is None:
        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # 브라우저 최대화
        chrome_options.add_argument("--disable-infobars")  # 정보 표시줄 비활성화
        chrome_options.add_argument("--disable-extensions")  # 확장 프로그램 비활성화
        chrome_options.add_argument(f"--user-agent={DEFAULT_USER_AGENT}")
        chrome_options.add_argument("--disable-gpu")  # GPU 가속 비활성화
        chrome_options.add_argument("--disable-dev-shm-usage")  # 공유 메모리 사용 비활성화
        chrome_options.add_argument("--no-sandbox")  # 샌드박스 비활성화
        
        # 브라우저 시작
        browser = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(browser, DEFAULT_TIMEOUT)
        
    return browser


def close_browser():
    """브라우저를 종료합니다."""
    global browser, wait
    
    if browser:
        try:
            browser.quit()
        except Exception:
            pass
        finally:
            browser = None
            wait = None


def element_to_dict(element) -> Dict[str, Any]:
    """Selenium 요소를 딕셔너리로 변환합니다."""
    try:
        # 요소 속성 수집
        attributes = {}
        for attr in ["id", "class", "name", "href", "src", "alt", "title", "type", "value"]:
            try:
                value = element.get_attribute(attr)
                if value:
                    attributes[attr] = value
            except:
                pass
        
        # 요소 위치 및 크기
        location = element.location
        size = element.size
        
        # 요소 정보 반환
        return {
            "tag": element.tag_name,
            "text": element.text,
            "attributes": attributes,
            "location": {
                "x": location["x"],
                "y": location["y"],
                "width": size["width"],
                "height": size["height"]
            },
            "is_displayed": element.is_displayed(),
            "is_enabled": element.is_enabled(),
            "element_id": element.id
        }
    except Exception as e:
        return {
            "error": str(e),
            "element_id": element.id if hasattr(element, "id") else None
        }


@mcp.tool()
def initialize_browser() -> Dict[str, Any]:
    """
    브라우저를 초기화하고 시작합니다.
    
    Returns:
        Dict: 브라우저 초기화 결과
    """
    try:
        browser = get_browser()
        
        # 브라우저 정보 수집
        user_agent = browser.execute_script("return navigator.userAgent;")
        browser_size = {
            "width": browser.execute_script("return window.innerWidth;"),
            "height": browser.execute_script("return window.innerHeight;")
        }
        
        return {
            "success": True,
            "message": "Browser initialized successfully",
            "browser_info": {
                "user_agent": user_agent,
                "window_size": browser_size,
                "browser_type": "Chrome"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to initialize browser"
        }


@mcp.tool()
def navigate_to_url(url: str) -> Dict[str, Any]:
    """
    지정된 URL로 이동합니다.
    
    Args:
        url: 이동할 URL
        
    Returns:
        Dict: 페이지 이동 결과
    """
    try:
        browser = get_browser()
        
        # URL 형식 확인 및 수정
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # 페이지 이동
        start_time = time.time()
        browser.get(url)
        load_time = time.time() - start_time
        
        # 페이지 정보 수집
        page_title = browser.title
        current_url = browser.current_url
        
        return {
            "success": True,
            "message": f"Navigated to {url}",
            "page_info": {
                "title": page_title,
                "url": current_url,
                "load_time_seconds": round(load_time, 2)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to navigate to {url}"
        }


@mcp.tool()
def search_on_web(query: str, search_engine: str = DEFAULT_SEARCH_ENGINE) -> Dict[str, Any]:
    """
    웹에서 검색을 수행합니다.
    
    Args:
        query: 검색할 쿼리
        search_engine: 검색 엔진 URL (기본값: Google)
        
    Returns:
        Dict: 검색 결과
    """
    try:
        browser = get_browser()
        
        # 검색 엔진으로 이동
        browser.get(search_engine)
        time.sleep(1)  # 페이지 로딩 대기
        
        # 검색창 찾기 및 쿼리 입력
        if "google.com" in search_engine:
            search_box = browser.find_element(By.NAME, "q")
        elif "bing.com" in search_engine:
            search_box = browser.find_element(By.NAME, "q")
        elif "yahoo.com" in search_engine:
            search_box = browser.find_element(By.NAME, "p")
        elif "naver.com" in search_engine:
            search_box = browser.find_element(By.NAME, "query")
        elif "daum.net" in search_engine:
            search_box = browser.find_element(By.NAME, "q")
        else:
            # 일반적인 검색창 찾기 시도
            search_box = browser.find_element(By.CSS_SELECTOR, "input[type='search'], input[type='text']")
        
        # 검색어 입력 및 검색 실행
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        
        # 검색 결과 로딩 대기
        time.sleep(2)
        
        # 검색 결과 정보 수집
        page_title = browser.title
        current_url = browser.current_url
        
        # 검색 결과 스크린샷 캡처
        screenshot = browser.get_screenshot_as_png()
        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
        
        return {
            "success": True,
            "message": f"Search completed for: {query}",
            "search_info": {
                "query": query,
                "search_engine": search_engine,
                "result_title": page_title,
                "result_url": current_url
            },
            "screenshot": screenshot_base64
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to search for: {query}"
        }


@mcp.tool()
def click_element(selector: str, selector_type: str = "css") -> Dict[str, Any]:
    """
    웹 페이지에서 요소를 클릭합니다.
    
    Args:
        selector: 요소 선택자
        selector_type: 선택자 유형 (css, xpath, id, class, name, tag, link_text)
        
    Returns:
        Dict: 클릭 결과
    """
    try:
        browser = get_browser()
        
        # 선택자 유형에 따라 요소 찾기
        if selector_type.lower() == "css":
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        elif selector_type.lower() == "xpath":
            element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
        elif selector_type.lower() == "id":
            element = wait.until(EC.element_to_be_clickable((By.ID, selector)))
        elif selector_type.lower() == "class":
            element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, selector)))
        elif selector_type.lower() == "name":
            element = wait.until(EC.element_to_be_clickable((By.NAME, selector)))
        elif selector_type.lower() == "tag":
            element = wait.until(EC.element_to_be_clickable((By.TAG_NAME, selector)))
        elif selector_type.lower() == "link_text":
            element = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, selector)))
        else:
            return {
                "success": False,
                "error": f"Invalid selector type: {selector_type}",
                "message": "Supported types: css, xpath, id, class, name, tag, link_text"
            }
        
        # 요소 정보 저장
        element_info = element_to_dict(element)
        
        # 요소 클릭
        element.click()
        
        # 페이지 변경 대기
        time.sleep(1)
        
        # 클릭 후 정보 수집
        page_title = browser.title
        current_url = browser.current_url
        
        return {
            "success": True,
            "message": f"Clicked element: {selector}",
            "element_info": element_info,
            "page_info": {
                "title": page_title,
                "url": current_url
            }
        }
    except TimeoutException:
        return {
            "success": False,
            "error": f"Element not found or not clickable: {selector}",
            "message": "Timeout waiting for element"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to click element: {selector}"
        }


@mcp.tool()
def find_elements(selector: str, selector_type: str = "css", limit: int = 10) -> Dict[str, Any]:
    """
    웹 페이지에서 요소들을 찾습니다.
    
    Args:
        selector: 요소 선택자
        selector_type: 선택자 유형 (css, xpath, id, class, name, tag, link_text)
        limit: 반환할 최대 요소 수
        
    Returns:
        Dict: 찾은 요소 목록
    """
    try:
        browser = get_browser()
        
        # 선택자 유형에 따라 요소 찾기
        if selector_type.lower() == "css":
            elements = browser.find_elements(By.CSS_SELECTOR, selector)
        elif selector_type.lower() == "xpath":
            elements = browser.find_elements(By.XPATH, selector)
        elif selector_type.lower() == "id":
            elements = browser.find_elements(By.ID, selector)
        elif selector_type.lower() == "class":
            elements = browser.find_elements(By.CLASS_NAME, selector)
        elif selector_type.lower() == "name":
            elements = browser.find_elements(By.NAME, selector)
        elif selector_type.lower() == "tag":
            elements = browser.find_elements(By.TAG_NAME, selector)
        elif selector_type.lower() == "link_text":
            elements = browser.find_elements(By.LINK_TEXT, selector)
        else:
            return {
                "success": False,
                "error": f"Invalid selector type: {selector_type}",
                "message": "Supported types: css, xpath, id, class, name, tag, link_text"
            }
        
        # 요소 정보 수집
        elements_info = []
        for i, element in enumerate(elements[:limit]):
            try:
                element_dict = element_to_dict(element)
                elements_info.append(element_dict)
            except:
                continue
        
        return {
            "success": True,
            "message": f"Found {len(elements_info)} elements matching: {selector}",
            "total_found": len(elements),
            "returned": len(elements_info),
            "elements": elements_info
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to find elements: {selector}"
        }


@mcp.tool()
def get_page_content() -> Dict[str, Any]:
    """
    현재 페이지의 내용을 가져옵니다.
    
    Returns:
        Dict: 페이지 내용 및 메타데이터
    """
    try:
        browser = get_browser()
        
        # 페이지 정보 수집
        page_title = browser.title
        current_url = browser.current_url
        
        # 페이지 텍스트 내용
        body_text = browser.find_element(By.TAG_NAME, "body").text
        
        # 메타 태그 정보
        meta_tags = {}
        for meta in browser.find_elements(By.TAG_NAME, "meta"):
            name = meta.get_attribute("name") or meta.get_attribute("property")
            content = meta.get_attribute("content")
            if name and content:
                meta_tags[name] = content
        
        # 링크 정보
        links = []
        for link in browser.find_elements(By.TAG_NAME, "a")[:20]:  # 처음 20개만
            href = link.get_attribute("href")
            text = link.text
            if href:
                links.append({"href": href, "text": text or "[이미지 또는 빈 링크]"})
        
        # 스크린샷 캡처
        screenshot = browser.get_screenshot_as_png()
        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
        
        return {
            "success": True,
            "message": "Page content retrieved successfully",
            "page_info": {
                "title": page_title,
                "url": current_url,
                "meta_tags": meta_tags
            },
            "content": {
                "text": body_text[:5000] + ("..." if len(body_text) > 5000 else ""),  # 텍스트 길이 제한
                "links": links
            },
            "screenshot": screenshot_base64
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get page content"
        }


@mcp.tool()
def fill_form(form_data: Dict[str, str], submit: bool = False) -> Dict[str, Any]:
    """
    웹 페이지의 폼을 작성합니다.
    
    Args:
        form_data: 필드 이름과 값의 딕셔너리
        submit: 폼 작성 후 제출 여부
        
    Returns:
        Dict: 폼 작성 결과
    """
    try:
        browser = get_browser()
        
        # 각 필드 작성
        filled_fields = []
        for field_name, value in form_data.items():
            try:
                # 다양한 선택자로 필드 찾기 시도
                field = None
                
                # ID로 찾기
                try:
                    field = browser.find_element(By.ID, field_name)
                except NoSuchElementException:
                    pass
                
                # 이름으로 찾기
                if field is None:
                    try:
                        field = browser.find_element(By.NAME, field_name)
                    except NoSuchElementException:
                        pass
                
                # CSS 선택자로 찾기
                if field is None:
                    try:
                        field = browser.find_element(By.CSS_SELECTOR, f"input[placeholder='{field_name}']")
                    except NoSuchElementException:
                        pass
                
                # 라벨 텍스트로 찾기
                if field is None:
                    try:
                        label = browser.find_element(By.XPATH, f"//label[contains(text(), '{field_name}')]")
                        field_id = label.get_attribute("for")
                        if field_id:
                            field = browser.find_element(By.ID, field_id)
                    except NoSuchElementException:
                        pass
                
                if field is None:
                    filled_fields.append({
                        "field": field_name,
                        "success": False,
                        "message": "Field not found"
                    })
                    continue
                
                # 필드 유형에 따라 처리
                tag_name = field.tag_name.lower()
                field_type = field.get_attribute("type")
                
                if tag_name == "select":
                    # 드롭다운 선택
                    from selenium.webdriver.support.ui import Select
                    select = Select(field)
                    select.select_by_visible_text(value)
                elif tag_name == "textarea" or (tag_name == "input" and field_type not in ["checkbox", "radio"]):
                    # 텍스트 입력
                    field.clear()
                    field.send_keys(value)
                elif tag_name == "input" and field_type == "checkbox":
                    # 체크박스
                    current_state = field.is_selected()
                    if (value.lower() in ["true", "yes", "1", "on"] and not current_state) or \
                       (value.lower() in ["false", "no", "0", "off"] and current_state):
                        field.click()
                elif tag_name == "input" and field_type == "radio":
                    # 라디오 버튼
                    if not field.is_selected():
                        field.click()
                
                filled_fields.append({
                    "field": field_name,
                    "success": True,
                    "message": f"Field filled with: {value}"
                })
                
            except Exception as e:
                filled_fields.append({
                    "field": field_name,
                    "success": False,
                    "message": f"Error: {str(e)}"
                })
        
        # 폼 제출
        if submit:
            try:
                # 제출 버튼 찾기 시도
                submit_button = None
                
                # type="submit" 속성으로 찾기
                try:
                    submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                except NoSuchElementException:
                    pass
                
                # 폼 태그 내 버튼 찾기
                if submit_button is None:
                    try:
                        submit_button = browser.find_element(By.CSS_SELECTOR, "form button")
                    except NoSuchElementException:
                        pass
                
                # 일반적인 제출 버튼 텍스트로 찾기
                if submit_button is None:
                    for text in ["Submit", "Login", "Sign in", "Register", "Send", "Search", "제출", "로그인", "가입", "검색"]:
                        try:
                            submit_button = browser.find_element(By.XPATH, f"//button[contains(text(), '{text}')] | //input[@value='{text}']")
                            break
                        except NoSuchElementException:
                            continue
                
                if submit_button:
                    submit_button.click()
                    time.sleep(2)  # 제출 후 페이지 로딩 대기
                    
                    return {
                        "success": True,
                        "message": "Form filled and submitted successfully",
                        "fields": filled_fields,
                        "submitted": True,
                        "page_info": {
                            "title": browser.title,
                            "url": browser.current_url
                        }
                    }
                else:
                    return {
                        "success": True,
                        "message": "Form filled but submit button not found",
                        "fields": filled_fields,
                        "submitted": False
                    }
            except Exception as e:
                return {
                    "success": True,
                    "message": f"Form filled but submission failed: {str(e)}",
                    "fields": filled_fields,
                    "submitted": False,
                    "submit_error": str(e)
                }
        
        return {
            "success": True,
            "message": "Form filled successfully",
            "fields": filled_fields,
            "submitted": False
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fill form"
        }


@mcp.tool()
def scroll_page(direction: str = "down", amount: int = 500) -> Dict[str, Any]:
    """
    페이지를 스크롤합니다.
    
    Args:
        direction: 스크롤 방향 (up, down, top, bottom)
        amount: 스크롤 양(픽셀)
        
    Returns:
        Dict: 스크롤 결과
    """
    try:
        browser = get_browser()
        
        # 현재 스크롤 위치
        current_position = browser.execute_script("return window.pageYOffset;")
        
        # 방향에 따라 스크롤
        if direction.lower() == "down":
            browser.execute_script(f"window.scrollBy(0, {amount});")
            message = f"Scrolled down by {amount} pixels"
        elif direction.lower() == "up":
            browser.execute_script(f"window.scrollBy(0, -{amount});")
            message = f"Scrolled up by {amount} pixels"
        elif direction.lower() == "top":
            browser.execute_script("window.scrollTo(0, 0);")
            message = "Scrolled to top of page"
        elif direction.lower() == "bottom":
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            message = "Scrolled to bottom of page"
        else:
            return {
                "success": False,
                "error": f"Invalid scroll direction: {direction}",
                "message": "Supported directions: up, down, top, bottom"
            }
        
        # 스크롤 후 위치
        new_position = browser.execute_script("return window.pageYOffset;")
        
        # 스크린샷 캡처
        screenshot = browser.get_screenshot_as_png()
        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
        
        return {
            "success": True,
            "message": message,
            "scroll_info": {
                "previous_position": current_position,
                "current_position": new_position,
                "change": new_position - current_position
            },
            "screenshot": screenshot_base64
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to scroll page"
        }


@mcp.tool()
def take_screenshot(full_page: bool = False) -> Dict[str, Any]:
    """
    현재 페이지의 스크린샷을 캡처합니다.
    
    Args:
        full_page: 전체 페이지 캡처 여부
        
    Returns:
        Dict: 스크린샷 결과
    """
    try:
        browser = get_browser()
        
        if full_page:
            # 전체 페이지 스크린샷 (스크롤하며 캡처)
            # 페이지 크기 가져오기
            total_width = browser.execute_script("return document.body.offsetWidth")
            total_height = browser.execute_script("return document.body.scrollHeight")
            viewport_width = browser.execute_script("return window.innerWidth")
            viewport_height = browser.execute_script("return window.innerHeight")
            
            # 원래 스크롤 위치 저장
            original_position = browser.execute_script("return window.pageYOffset")
            
            # 새 이미지 생성
            from PIL import Image
            full_screenshot = Image.new('RGB', (viewport_width, total_height))
            
            # 스크롤하며 캡처
            for i in range(0, total_height, viewport_height):
                # 스크롤
                browser.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(0.2)  # 렌더링 대기
                
                # 스크린샷 캡처
                screenshot = browser.get_screenshot_as_png()
                image = Image.open(io.BytesIO(screenshot))
                
                # 이미지 합치기
                full_screenshot.paste(image, (0, i))
                
                # 마지막 스크롤이면 종료
                if i + viewport_height >= total_height:
                    break
            
            # 원래 위치로 스크롤 복원
            browser.execute_script(f"window.scrollTo(0, {original_position});")
            
            # 이미지를 base64로 인코딩
            buffer = io.BytesIO()
            full_screenshot.save(buffer, format='PNG')
            buffer.seek(0)
            screenshot_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return {
                "success": True,
                "message": "Full page screenshot captured",
                "screenshot": screenshot_base64,
                "width": viewport_width,
                "height": total_height,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 현재 화면 스크린샷
            screenshot = browser.get_screenshot_as_png()
            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
            
            # 화면 크기
            viewport_width = browser.execute_script("return window.innerWidth")
            viewport_height = browser.execute_script("return window.innerHeight")
            
            return {
                "success": True,
                "message": "Screenshot captured",
                "screenshot": screenshot_base64,
                "width": viewport_width,
                "height": viewport_height,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to take screenshot"
        }


@mcp.tool()
def extract_text_from_element(selector: str, selector_type: str = "css") -> Dict[str, Any]:
    """
    특정 요소에서 텍스트를 추출합니다.
    
    Args:
        selector: 요소 선택자
        selector_type: 선택자 유형 (css, xpath, id, class, name, tag, link_text)
        
    Returns:
        Dict: 추출된 텍스트
    """
    try:
        browser = get_browser()
        
        # 선택자 유형에 따라 요소 찾기
        if selector_type.lower() == "css":
            element = browser.find_element(By.CSS_SELECTOR, selector)
        elif selector_type.lower() == "xpath":
            element = browser.find_element(By.XPATH, selector)
        elif selector_type.lower() == "id":
            element = browser.find_element(By.ID, selector)
        elif selector_type.lower() == "class":
            element = browser.find_element(By.CLASS_NAME, selector)
        elif selector_type.lower() == "name":
            element = browser.find_element(By.NAME, selector)
        elif selector_type.lower() == "tag":
            element = browser.find_element(By.TAG_NAME, selector)
        elif selector_type.lower() == "link_text":
            element = browser.find_element(By.LINK_TEXT, selector)
        else:
            return {
                "success": False,
                "error": f"Invalid selector type: {selector_type}",
                "message": "Supported types: css, xpath, id, class, name, tag, link_text"
            }
        
        # 요소 정보 수집
        element_text = element.text
        element_html = element.get_attribute("outerHTML")
        element_info = element_to_dict(element)
        
        return {
            "success": True,
            "message": f"Text extracted from element: {selector}",
            "text": element_text,
            "html": element_html,
            "element_info": element_info
        }
    except NoSuchElementException:
        return {
            "success": False,
            "error": f"Element not found: {selector}",
            "message": "Check the selector and try again"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to extract text from element: {selector}"
        }


@mcp.tool()
def execute_javascript(script: str) -> Dict[str, Any]:
    """
    자바스크립트 코드를 실행합니다.
    
    Args:
        script: 실행할 자바스크립트 코드
        
    Returns:
        Dict: 실행 결과
    """
    try:
        browser = get_browser()
        
        # 스크립트 실행
        result = browser.execute_script(f"return (function() {{ {script} }})();")
        
        # 결과 처리
        if result is None:
            result_str = "null"
        elif isinstance(result, (dict, list)):
            result_str = json.dumps(result, ensure_ascii=False)
        else:
            result_str = str(result)
        
        return {
            "success": True,
            "message": "JavaScript executed successfully",
            "result": result_str
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to execute JavaScript"
        }


@mcp.tool()
def close_browser_session() -> Dict[str, Any]:
    """
    브라우저 세션을 종료합니다.
    
    Returns:
        Dict: 종료 결과
    """
    try:
        close_browser()
        return {
            "success": True,
            "message": "Browser session closed successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to close browser session"
        }


async def main():
    """MCP 서버 실행"""
    try:
        # 서버 실행
        await mcp.run()
    finally:
        # 종료 시 브라우저 닫기
        close_browser()


if __name__ == "__main__":
    print("🌐 Browser Control MCP Server")
    print("🤖 FastMCP를 이용한 브라우저 제어 도구")
    print("🚀 서버를 시작합니다...")
    
    try:
        # 이미 실행 중인 이벤트 루프가 있는지 확인
        try:
            loop = asyncio.get_running_loop()
            print("⚠️  이미 실행 중인 이벤트 루프가 감지되었습니다.")
            print("🔧 nest_asyncio를 사용하여 중첩 이벤트 루프를 활성화합니다.")
            
            # nest_asyncio를 사용하여 중첩된 이벤트 루프 허용
            try:
                import nest_asyncio
                nest_asyncio.apply()
                asyncio.run(main())
            except ImportError:
                print("❌ nest_asyncio가 설치되지 않았습니다.")
                print("📦 설치 명령: pip install nest-asyncio")
                print("🔄 대신 create_task를 사용합니다.")
                loop.create_task(main())
                
        except RuntimeError:
            # 실행 중인 이벤트 루프가 없음
            asyncio.run(main())
            
    except KeyboardInterrupt:
        print("\n⏹️  서버를 종료합니다.")
        close_browser()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("💡 해결 방법:")
        print("   1. 새로운 터미널에서 실행해보세요")
        print("   2. pip install selenium nest-asyncio 후 재시도하세요")
        print("   3. 다른 Python 환경에서 실행해보세요")
        close_browser()
