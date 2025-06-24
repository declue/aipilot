#!/usr/bin/env python3
"""
Process Manager MCP Server
PC의 프로세스를 관리하고 시스템 자원 사용량을 모니터링하는 도구들을 제공합니다.
태스크 관리자와 유사한 기능을 MCP 인터페이스를 통해 사용할 수 있습니다.
"""

import os
import sys
import time
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import psutil
from mcp.server.fastmcp import FastMCP

# Create MCP Server
app = FastMCP(
    title="Process Manager Server",
    description="A server for process and system resource management",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
DEFAULT_PROCESS_LIMIT = 50  # 기본 프로세스 목록 제한
DEFAULT_SORT_BY = "cpu_percent"  # 기본 정렬 기준
DEFAULT_INTERVAL = 0.1  # CPU 사용량 측정 간격(초)


@dataclass
class ProcessInfo:
    """프로세스 정보를 담는 데이터 클래스"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_usage: int
    username: str
    create_time: float
    cmdline: List[str]
    num_threads: int
    parent_pid: Optional[int]
    children: List[int]


@dataclass
class SystemResourceInfo:
    """시스템 자원 정보를 담는 데이터 클래스"""
    cpu_percent: float
    cpu_count: int
    cpu_freq: Dict[str, float]
    memory_total: int
    memory_available: int
    memory_used: int
    memory_percent: float
    disk_usage: Dict[str, Dict[str, Any]]
    network_io: Dict[str, Dict[str, int]]
    boot_time: float
    timestamp: str


class ProcessManagerService:
    """프로세스 관리 서비스 클래스"""
    
    def __init__(self):
        """서비스 초기화"""
        # 초기 CPU 사용량 측정을 위한 준비
        psutil.cpu_percent(interval=None)
    
    def get_process_list(self, sort_by: str = DEFAULT_SORT_BY, limit: int = DEFAULT_PROCESS_LIMIT, 
                         filter_name: Optional[str] = None) -> List[ProcessInfo]:
        """실행 중인 프로세스 목록을 가져옵니다."""
        processes = []
        
        # 모든 프로세스 정보 수집
        for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 'cmdline', 
                                         'cpu_percent', 'memory_percent', 'memory_info',
                                         'create_time', 'num_threads', 'ppid']):
            try:
                # 프로세스 정보 추출
                proc_info = proc.info
                
                # 이름 필터링 (지정된 경우)
                if filter_name and filter_name.lower() not in proc_info['name'].lower():
                    continue
                
                # CPU 사용량 업데이트
                proc.cpu_percent(interval=DEFAULT_INTERVAL)
                
                # 자식 프로세스 목록
                try:
                    children = [child.pid for child in proc.children()]
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    children = []
                
                # ProcessInfo 객체 생성
                process = ProcessInfo(
                    pid=proc_info['pid'],
                    name=proc_info['name'],
                    status=proc_info['status'],
                    cpu_percent=proc_info['cpu_percent'],
                    memory_percent=proc_info['memory_percent'] or 0.0,
                    memory_usage=proc_info['memory_info'].rss if proc_info['memory_info'] else 0,
                    username=proc_info['username'] or '',
                    create_time=proc_info['create_time'],
                    cmdline=proc_info['cmdline'] or [],
                    num_threads=proc_info['num_threads'],
                    parent_pid=proc_info['ppid'],
                    children=children
                )
                
                processes.append(process)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 프로세스가 사라졌거나 접근 권한이 없는 경우 무시
                continue
        
        # 정렬 및 제한
        if sort_by == "memory_percent":
            processes.sort(key=lambda x: x.memory_percent, reverse=True)
        elif sort_by == "memory_usage":
            processes.sort(key=lambda x: x.memory_usage, reverse=True)
        elif sort_by == "cpu_percent":
            processes.sort(key=lambda x: x.cpu_percent, reverse=True)
        elif sort_by == "pid":
            processes.sort(key=lambda x: x.pid)
        elif sort_by == "name":
            processes.sort(key=lambda x: x.name.lower())
        elif sort_by == "time":
            processes.sort(key=lambda x: x.create_time, reverse=True)
        
        # 결과 제한
        return processes[:limit]
    
    def get_process_detail(self, pid: int) -> Optional[Dict[str, Any]]:
        """특정 프로세스의 상세 정보를 가져옵니다."""
        try:
            proc = psutil.Process(pid)
            
            # 기본 정보
            with proc.oneshot():  # 여러 정보를 한 번에 가져오기 위한 최적화
                name = proc.name()
                status = proc.status()
                create_time = proc.create_time()
                cpu_percent = proc.cpu_percent(interval=DEFAULT_INTERVAL)
                memory_info = proc.memory_info()
                memory_percent = proc.memory_percent()
                username = proc.username()
                cmdline = proc.cmdline()
                cwd = proc.cwd()
                parent = proc.parent()
                children = proc.children()
                num_threads = proc.num_threads()
                threads = proc.threads()
                nice = proc.nice()
                io_counters = proc.io_counters() if hasattr(proc, 'io_counters') else None
                open_files = proc.open_files()
                connections = proc.connections()
                environ = proc.environ()
                
            # 상세 정보 구성
            detail = {
                "pid": pid,
                "name": name,
                "status": status,
                "cpu_percent": cpu_percent,
                "memory": {
                    "rss": memory_info.rss,
                    "vms": memory_info.vms,
                    "percent": memory_percent
                },
                "user": username,
                "create_time": create_time,
                "create_time_formatted": datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S'),
                "cmdline": cmdline,
                "cwd": cwd,
                "parent": parent.pid if parent else None,
                "children": [child.pid for child in children],
                "threads": {
                    "count": num_threads,
                    "list": [{"id": t.id, "user_time": t.user_time, "system_time": t.system_time} for t in threads]
                },
                "nice": nice,
                "open_files": [{"path": f.path, "fd": f.fd} for f in open_files],
                "connections": [
                    {
                        "fd": c.fd,
                        "family": str(c.family),
                        "type": str(c.type),
                        "local_addr": f"{c.laddr.ip}:{c.laddr.port}" if hasattr(c.laddr, 'ip') else str(c.laddr),
                        "remote_addr": f"{c.raddr.ip}:{c.raddr.port}" if hasattr(c.raddr, 'ip') and c.raddr else None,
                        "status": c.status
                    } for c in connections
                ]
            }
            
            # IO 카운터 추가 (가능한 경우)
            if io_counters:
                detail["io"] = {
                    "read_count": io_counters.read_count,
                    "write_count": io_counters.write_count,
                    "read_bytes": io_counters.read_bytes,
                    "write_bytes": io_counters.write_bytes
                }
            
            # 환경 변수 (민감 정보 필터링)
            filtered_env = {}
            sensitive_keys = ['password', 'token', 'secret', 'key', 'credential', 'auth']
            for key, value in environ.items():
                # 민감한 정보는 마스킹
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    filtered_env[key] = "********"
                else:
                    filtered_env[key] = value
            
            detail["environment"] = filtered_env
            
            return detail
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            return None
    
    def get_system_resources(self) -> SystemResourceInfo:
        """시스템 자원 사용 정보를 가져옵니다."""
        # CPU 정보
        cpu_percent = psutil.cpu_percent(interval=DEFAULT_INTERVAL)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        
        # 디스크 정보
        disk_usage = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "device": partition.device,
                    "fstype": partition.fstype
                }
            except (PermissionError, OSError):
                # 일부 디스크는 접근 권한이 없을 수 있음
                continue
        
        # 네트워크 정보
        network_io = {}
        net_io = psutil.net_io_counters(pernic=True)
        for nic, counters in net_io.items():
            network_io[nic] = {
                "bytes_sent": counters.bytes_sent,
                "bytes_recv": counters.bytes_recv,
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errin": counters.errin,
                "errout": counters.errout,
                "dropin": counters.dropin,
                "dropout": counters.dropout
            }
        
        # 시스템 부팅 시간
        boot_time = psutil.boot_time()
        
        return SystemResourceInfo(
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            cpu_freq={
                "current": cpu_freq.current if cpu_freq else 0,
                "min": cpu_freq.min if cpu_freq and hasattr(cpu_freq, 'min') else 0,
                "max": cpu_freq.max if cpu_freq and hasattr(cpu_freq, 'max') else 0
            },
            memory_total=memory.total,
            memory_available=memory.available,
            memory_used=memory.used,
            memory_percent=memory.percent,
            disk_usage=disk_usage,
            network_io=network_io,
            boot_time=boot_time,
            timestamp=datetime.now().isoformat()
        )
    
    def kill_process(self, pid: int) -> bool:
        """프로세스를 종료합니다."""
        try:
            process = psutil.Process(pid)
            process.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    def terminate_process(self, pid: int) -> bool:
        """프로세스를 정상 종료합니다."""
        try:
            process = psutil.Process(pid)
            process.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    def suspend_process(self, pid: int) -> bool:
        """프로세스를 일시 중지합니다."""
        try:
            process = psutil.Process(pid)
            process.suspend()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    def resume_process(self, pid: int) -> bool:
        """일시 중지된 프로세스를 재개합니다."""
        try:
            process = psutil.Process(pid)
            process.resume()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    def start_process(self, command: str, shell: bool = True) -> Optional[int]:
        """새 프로세스를 시작합니다."""
        try:
            if shell:
                # 쉘을 통해 명령 실행
                process = subprocess.Popen(command, shell=True)
            else:
                # 명령을 직접 실행
                process = subprocess.Popen(command.split())
            
            return process.pid
        except (OSError, ValueError, subprocess.SubprocessError):
            return None


# 전역 서비스 인스턴스
process_manager = ProcessManagerService()


@app.tool()
def list_processes(sort_by: str = DEFAULT_SORT_BY, limit: int = DEFAULT_PROCESS_LIMIT, 
                  filter_name: Optional[str] = None) -> dict:
    """
    실행 중인 프로세스 목록을 반환합니다.

    Args:
        sort_by: 정렬 기준 (cpu_percent, memory_percent, memory_usage, pid, name, time)
        limit: 반환할 최대 프로세스 수
        filter_name: 프로세스 이름으로 필터링 (부분 일치)

    Returns:
        dict: 프로세스 목록 정보를 포함한 딕셔너리
    """
    try:
        # 프로세스 목록 가져오기
        processes = process_manager.get_process_list(sort_by, limit, filter_name)
        
        # 결과 포맷팅
        formatted_processes = []
        for proc in processes:
            formatted_processes.append({
                "pid": proc.pid,
                "name": proc.name,
                "status": proc.status,
                "cpu_percent": proc.cpu_percent,
                "memory_percent": proc.memory_percent,
                "memory_usage": proc.memory_usage,
                "memory_usage_formatted": format_bytes(proc.memory_usage),
                "username": proc.username,
                "create_time": proc.create_time,
                "create_time_formatted": datetime.fromtimestamp(proc.create_time).strftime('%Y-%m-%d %H:%M:%S'),
                "num_threads": proc.num_threads,
                "parent_pid": proc.parent_pid,
                "children_count": len(proc.children)
            })
        
        return {
            "result": {
                "processes": formatted_processes,
                "count": len(formatted_processes),
                "sort_by": sort_by,
                "filter": filter_name,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"프로세스 목록 조회 중 오류 발생: {str(e)}"}


@app.tool()
def get_process_details(pid: int) -> dict:
    """
    특정 프로세스의 상세 정보를 반환합니다.

    Args:
        pid: 프로세스 ID

    Returns:
        dict: 프로세스 상세 정보를 포함한 딕셔너리
    """
    try:
        # 프로세스 상세 정보 가져오기
        process_detail = process_manager.get_process_detail(pid)
        
        if not process_detail:
            return {"error": f"프로세스 ID {pid}를 찾을 수 없거나 접근할 수 없습니다."}
        
        # 메모리 사용량 포맷팅
        process_detail["memory"]["rss_formatted"] = format_bytes(process_detail["memory"]["rss"])
        process_detail["memory"]["vms_formatted"] = format_bytes(process_detail["memory"]["vms"])
        
        return {
            "result": {
                "process": process_detail,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"프로세스 상세 정보 조회 중 오류 발생: {str(e)}"}


@app.tool()
def get_system_info() -> dict:
    """
    시스템 자원 사용 정보를 반환합니다.

    Returns:
        dict: 시스템 자원 정보를 포함한 딕셔너리
    """
    try:
        # 시스템 자원 정보 가져오기
        resources = process_manager.get_system_resources()
        
        # 결과 포맷팅
        formatted_resources = {
            "cpu": {
                "percent": resources.cpu_percent,
                "count": resources.cpu_count,
                "frequency": resources.cpu_freq
            },
            "memory": {
                "total": resources.memory_total,
                "total_formatted": format_bytes(resources.memory_total),
                "available": resources.memory_available,
                "available_formatted": format_bytes(resources.memory_available),
                "used": resources.memory_used,
                "used_formatted": format_bytes(resources.memory_used),
                "percent": resources.memory_percent
            },
            "disk": {
                mountpoint: {
                    **info,
                    "total_formatted": format_bytes(info["total"]),
                    "used_formatted": format_bytes(info["used"]),
                    "free_formatted": format_bytes(info["free"])
                }
                for mountpoint, info in resources.disk_usage.items()
            },
            "network": {
                nic: {
                    **info,
                    "bytes_sent_formatted": format_bytes(info["bytes_sent"]),
                    "bytes_recv_formatted": format_bytes(info["bytes_recv"])
                }
                for nic, info in resources.network_io.items()
            },
            "boot_time": resources.boot_time,
            "boot_time_formatted": datetime.fromtimestamp(resources.boot_time).strftime('%Y-%m-%d %H:%M:%S'),
            "uptime_seconds": time.time() - resources.boot_time,
            "uptime_formatted": format_uptime(time.time() - resources.boot_time),
            "timestamp": resources.timestamp
        }
        
        return {
            "result": formatted_resources
        }
        
    except Exception as e:
        return {"error": f"시스템 정보 조회 중 오류 발생: {str(e)}"}


@app.tool()
def kill_process(pid: int) -> dict:
    """
    프로세스를 강제 종료합니다.

    Args:
        pid: 종료할 프로세스 ID

    Returns:
        dict: 종료 결과를 포함한 딕셔너리
    """
    try:
        # 프로세스 종료
        success = process_manager.kill_process(pid)
        
        if success:
            return {
                "result": {
                    "success": True,
                    "message": f"프로세스 ID {pid}가 강제 종료되었습니다.",
                    "pid": pid,
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {"error": f"프로세스 ID {pid}를 종료할 수 없습니다. 권한이 없거나 프로세스가 존재하지 않습니다."}
        
    except Exception as e:
        return {"error": f"프로세스 종료 중 오류 발생: {str(e)}"}


@app.tool()
def terminate_process(pid: int) -> dict:
    """
    프로세스를 정상 종료합니다.

    Args:
        pid: 종료할 프로세스 ID

    Returns:
        dict: 종료 결과를 포함한 딕셔너리
    """
    try:
        # 프로세스 정상 종료
        success = process_manager.terminate_process(pid)
        
        if success:
            return {
                "result": {
                    "success": True,
                    "message": f"프로세스 ID {pid}에 종료 신호를 보냈습니다.",
                    "pid": pid,
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {"error": f"프로세스 ID {pid}를 종료할 수 없습니다. 권한이 없거나 프로세스가 존재하지 않습니다."}
        
    except Exception as e:
        return {"error": f"프로세스 종료 중 오류 발생: {str(e)}"}


@app.tool()
def suspend_process(pid: int) -> dict:
    """
    프로세스를 일시 중지합니다.

    Args:
        pid: 일시 중지할 프로세스 ID

    Returns:
        dict: 일시 중지 결과를 포함한 딕셔너리
    """
    try:
        # 프로세스 일시 중지
        success = process_manager.suspend_process(pid)
        
        if success:
            return {
                "result": {
                    "success": True,
                    "message": f"프로세스 ID {pid}가 일시 중지되었습니다.",
                    "pid": pid,
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {"error": f"프로세스 ID {pid}를 일시 중지할 수 없습니다. 권한이 없거나 프로세스가 존재하지 않습니다."}
        
    except Exception as e:
        return {"error": f"프로세스 일시 중지 중 오류 발생: {str(e)}"}


@app.tool()
def resume_process(pid: int) -> dict:
    """
    일시 중지된 프로세스를 재개합니다.

    Args:
        pid: 재개할 프로세스 ID

    Returns:
        dict: 재개 결과를 포함한 딕셔너리
    """
    try:
        # 프로세스 재개
        success = process_manager.resume_process(pid)
        
        if success:
            return {
                "result": {
                    "success": True,
                    "message": f"프로세스 ID {pid}가 재개되었습니다.",
                    "pid": pid,
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {"error": f"프로세스 ID {pid}를 재개할 수 없습니다. 권한이 없거나 프로세스가 존재하지 않습니다."}
        
    except Exception as e:
        return {"error": f"프로세스 재개 중 오류 발생: {str(e)}"}


@app.tool()
def start_process(command: str, shell: bool = True) -> dict:
    """
    새 프로세스를 시작합니다.

    Args:
        command: 실행할 명령어
        shell: 쉘을 통해 실행할지 여부

    Returns:
        dict: 프로세스 시작 결과를 포함한 딕셔너리
    """
    try:
        # 프로세스 시작
        pid = process_manager.start_process(command, shell)
        
        if pid:
            return {
                "result": {
                    "success": True,
                    "message": f"프로세스가 시작되었습니다. PID: {pid}",
                    "pid": pid,
                    "command": command,
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {"error": f"프로세스를 시작할 수 없습니다: {command}"}
        
    except Exception as e:
        return {"error": f"프로세스 시작 중 오류 발생: {str(e)}"}


@app.tool()
def find_process_by_name(name: str, case_sensitive: bool = False) -> dict:
    """
    이름으로 프로세스를 검색합니다.

    Args:
        name: 검색할 프로세스 이름
        case_sensitive: 대소문자 구분 여부

    Returns:
        dict: 검색 결과를 포함한 딕셔너리
    """
    try:
        # 모든 프로세스 검색
        all_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                proc_name = proc_info['name']
                
                # 대소문자 구분 여부에 따라 비교
                if (case_sensitive and name in proc_name) or \
                   (not case_sensitive and name.lower() in proc_name.lower()):
                    all_processes.append({
                        "pid": proc_info['pid'],
                        "name": proc_name,
                        "status": proc_info['status'],
                        "cpu_percent": proc_info['cpu_percent'],
                        "memory_percent": proc_info['memory_percent'] or 0.0
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # CPU 사용량으로 정렬
        all_processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        
        return {
            "result": {
                "processes": all_processes,
                "count": len(all_processes),
                "search_term": name,
                "case_sensitive": case_sensitive,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"프로세스 검색 중 오류 발생: {str(e)}"}


@app.tool()
def get_process_tree() -> dict:
    """
    프로세스 트리 구조를 반환합니다.

    Returns:
        dict: 프로세스 트리 구조를 포함한 딕셔너리
    """
    try:
        # 모든 프로세스 정보 수집
        processes = {}
        for proc in psutil.process_iter(['pid', 'name', 'ppid']):
            try:
                proc_info = proc.info
                processes[proc_info['pid']] = {
                    "pid": proc_info['pid'],
                    "name": proc_info['name'],
                    "parent": proc_info['ppid'],
                    "children": []
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # 부모-자식 관계 구성
        process_tree = {}
        for pid, proc in processes.items():
            parent_pid = proc['parent']
            if parent_pid in processes:
                processes[parent_pid]['children'].append(pid)
            
            # 루트 프로세스 (부모가 없거나 부모가 존재하지 않는 경우)
            if parent_pid == 0 or parent_pid not in processes:
                process_tree[pid] = proc
        
        # 트리 구조 재귀적으로 구성
        def build_tree(pid):
            proc = processes[pid]
            children = []
            for child_pid in proc['children']:
                if child_pid in processes:
                    children.append(build_tree(child_pid))
            return {
                "pid": proc['pid'],
                "name": proc['name'],
                "children": children
            }
        
        # 최종 트리 구조 구성
        final_tree = []
        for pid in process_tree:
            final_tree.append(build_tree(pid))
        
        return {
            "result": {
                "process_tree": final_tree,
                "count": len(processes),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {"error": f"프로세스 트리 구성 중 오류 발생: {str(e)}"}


def format_bytes(bytes_value: int) -> str:
    """바이트 단위를 사람이 읽기 쉬운 형식으로 변환합니다."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_uptime(seconds: float) -> str:
    """초 단위 시간을 사람이 읽기 쉬운 형식으로 변환합니다."""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}일 {hours}시간 {minutes}분"
    elif hours > 0:
        return f"{hours}시간 {minutes}분 {seconds}초"
    elif minutes > 0:
        return f"{minutes}분 {seconds}초"
    else:
        return f"{seconds}초"


if __name__ == "__main__":
    print("🖥️ Process Manager MCP Server")
    print("🔧 FastMCP를 이용한 프로세스 및 시스템 자원 관리 도구")
    print("🚀 서버를 시작합니다...")
    
    app.run(transport=TRANSPORT)