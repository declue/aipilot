#!/usr/bin/env python3
"""
Process Monitoring MCP Server
현재 사용중인 OS의 프로세스 현황을 조회하는 도구를 제공합니다.
프로세스별 CPU, 메모리 등 다양한 정보를 조회할 수 있습니다.
"""

import logging
import os
import sys
import time
import json
import platform
import signal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

try:
    import psutil
except ImportError:
    print("psutil 라이브러리가 설치되어 있지 않습니다. 설치하려면: pip install psutil")
    sys.exit(1)

from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 process_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "process_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("PROCESS_TOOL_LOG_LEVEL", "WARNING").upper()
log_level_int = getattr(logging, log_level, logging.WARNING)

logging.basicConfig(
    level=log_level_int,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(log_file_path),
              logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# INFO 레벨 로그는 환경 변수가 DEBUG나 INFO로 설정된 경우에만 출력
if log_level_int <= logging.INFO:
    logger.info("Process Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Process Monitoring Server",
    description="A server for process monitoring operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
DEFAULT_PROCESS_LIMIT = 50  # 기본 프로세스 조회 개수 제한
DEFAULT_SORT_BY = "cpu_percent"  # 기본 정렬 기준
DEFAULT_SORT_ORDER = "desc"  # 기본 정렬 순서


@dataclass
class ProcessInfo:
    """프로세스 정보를 담는 데이터 클래스"""
    pid: int
    name: str
    status: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_rss: int = 0  # 실제 물리 메모리 사용량 (바이트)
    memory_vms: int = 0  # 가상 메모리 사용량 (바이트)
    username: str = ""
    create_time: str = ""
    cmdline: List[str] = field(default_factory=list)
    num_threads: int = 0
    parent_pid: int = 0
    parent_name: str = ""
    children: List[int] = field(default_factory=list)
    nice: int = 0
    cwd: str = ""
    exe: str = ""
    open_files_count: int = 0
    connections_count: int = 0
    io_read_count: int = 0
    io_write_count: int = 0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    cpu_times_user: float = 0.0
    cpu_times_system: float = 0.0
    cpu_affinity: List[int] = field(default_factory=list)
    error: str = ""


@dataclass
class SystemInfo:
    """시스템 정보를 담는 데이터 클래스"""
    cpu_count_physical: int = 0
    cpu_count_logical: int = 0
    cpu_percent: float = 0.0
    cpu_percent_per_cpu: List[float] = field(default_factory=list)
    memory_total: int = 0
    memory_available: int = 0
    memory_used: int = 0
    memory_percent: float = 0.0
    swap_total: int = 0
    swap_used: int = 0
    swap_free: int = 0
    swap_percent: float = 0.0
    disk_usage: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    boot_time: str = ""
    platform: str = ""
    platform_version: str = ""
    python_version: str = ""
    hostname: str = ""
    uptime: str = ""
    process_count: int = 0
    thread_count: int = 0
    error: str = ""


class ProcessMonitoringService:
    """프로세스 모니터링 서비스 클래스"""

    def __init__(self):
        """프로세스 모니터링 서비스 초기화"""
        self.is_windows = platform.system().lower() == "windows"
        self.is_mac = platform.system().lower() == "darwin"
        self.is_linux = platform.system().lower() == "linux"

    def _get_process_info(self, proc: psutil.Process) -> ProcessInfo:
        """
        단일 프로세스 정보를 가져옵니다.
        
        Args:
            proc: psutil.Process 객체
            
        Returns:
            ProcessInfo: 프로세스 정보
        """
        try:
            # 기본 정보
            pid = proc.pid
            name = proc.name()
            status = proc.status()
            
            # CPU 및 메모리 사용량
            try:
                cpu_percent = proc.cpu_percent(interval=0.1)
            except:
                cpu_percent = 0.0
                
            try:
                memory_percent = proc.memory_percent()
            except:
                memory_percent = 0.0
                
            try:
                memory_info = proc.memory_info()
                memory_rss = memory_info.rss
                memory_vms = memory_info.vms
            except:
                memory_rss = 0
                memory_vms = 0
            
            # 사용자 정보
            try:
                username = proc.username()
            except:
                username = ""
            
            # 생성 시간
            try:
                create_time = datetime.fromtimestamp(proc.create_time()).strftime("%Y-%m-%d %H:%M:%S")
            except:
                create_time = ""
            
            # 명령줄
            try:
                cmdline = proc.cmdline()
            except:
                cmdline = []
            
            # 스레드 수
            try:
                num_threads = proc.num_threads()
            except:
                num_threads = 0
            
            # 부모 프로세스 정보
            parent_pid = 0
            parent_name = ""
            try:
                parent = proc.parent()
                if parent:
                    parent_pid = parent.pid
                    parent_name = parent.name()
            except:
                pass
            
            # 자식 프로세스 정보
            children = []
            try:
                for child in proc.children():
                    children.append(child.pid)
            except:
                pass
            
            # 우선순위 (nice)
            try:
                nice = proc.nice()
            except:
                nice = 0
            
            # 작업 디렉토리
            try:
                cwd = proc.cwd()
            except:
                cwd = ""
            
            # 실행 파일 경로
            try:
                exe = proc.exe()
            except:
                exe = ""
            
            # 열린 파일 수
            try:
                open_files_count = len(proc.open_files())
            except:
                open_files_count = 0
            
            # 네트워크 연결 수
            try:
                connections_count = len(proc.connections())
            except:
                connections_count = 0
            
            # I/O 통계
            io_read_count = 0
            io_write_count = 0
            io_read_bytes = 0
            io_write_bytes = 0
            try:
                io_counters = proc.io_counters()
                io_read_count = io_counters.read_count
                io_write_count = io_counters.write_count
                io_read_bytes = io_counters.read_bytes
                io_write_bytes = io_counters.write_bytes
            except:
                pass
            
            # CPU 시간
            cpu_times_user = 0.0
            cpu_times_system = 0.0
            try:
                cpu_times = proc.cpu_times()
                cpu_times_user = cpu_times.user
                cpu_times_system = cpu_times.system
            except:
                pass
            
            # CPU 친화도
            cpu_affinity = []
            try:
                cpu_affinity = proc.cpu_affinity()
            except:
                pass
            
            return ProcessInfo(
                pid=pid,
                name=name,
                status=status,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_rss=memory_rss,
                memory_vms=memory_vms,
                username=username,
                create_time=create_time,
                cmdline=cmdline,
                num_threads=num_threads,
                parent_pid=parent_pid,
                parent_name=parent_name,
                children=children,
                nice=nice,
                cwd=cwd,
                exe=exe,
                open_files_count=open_files_count,
                connections_count=connections_count,
                io_read_count=io_read_count,
                io_write_count=io_write_count,
                io_read_bytes=io_read_bytes,
                io_write_bytes=io_write_bytes,
                cpu_times_user=cpu_times_user,
                cpu_times_system=cpu_times_system,
                cpu_affinity=cpu_affinity
            )
            
        except psutil.NoSuchProcess:
            return ProcessInfo(
                pid=proc.pid,
                name="",
                status="terminated",
                error="프로세스가 존재하지 않습니다"
            )
        except psutil.AccessDenied:
            return ProcessInfo(
                pid=proc.pid,
                name=proc.name() if hasattr(proc, "name") else "",
                status="access denied",
                error="프로세스 정보에 접근할 권한이 없습니다"
            )
        except Exception as e:
            logger.error(f"프로세스 정보 가져오기 중 예외 발생: {e}")
            return ProcessInfo(
                pid=proc.pid if hasattr(proc, "pid") else 0,
                name=proc.name() if hasattr(proc, "name") else "",
                status="error",
                error=f"프로세스 정보를 가져오는 중 오류 발생: {str(e)}"
            )

    def get_process_list(self, limit: int = DEFAULT_PROCESS_LIMIT, sort_by: str = DEFAULT_SORT_BY, 
                         sort_order: str = DEFAULT_SORT_ORDER, name_filter: str = None, 
                         username_filter: str = None, status_filter: str = None) -> List[ProcessInfo]:
        """
        프로세스 목록을 가져옵니다.
        
        Args:
            limit: 반환할 프로세스 수 제한
            sort_by: 정렬 기준 (cpu_percent, memory_percent, pid, name, create_time)
            sort_order: 정렬 순서 (asc, desc)
            name_filter: 프로세스 이름 필터
            username_filter: 사용자 이름 필터
            status_filter: 상태 필터 (running, sleeping, disk-sleep, stopped, zombie, dead)
            
        Returns:
            List[ProcessInfo]: 프로세스 정보 목록
        """
        try:
            # 모든 프로세스 가져오기
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'status']):
                try:
                    # 필터 적용
                    if name_filter and name_filter.lower() not in proc.info['name'].lower():
                        continue
                    if username_filter and (not proc.info['username'] or username_filter.lower() not in proc.info['username'].lower()):
                        continue
                    if status_filter and (not proc.info['status'] or status_filter.lower() != proc.info['status'].lower()):
                        continue
                    
                    # 프로세스 정보 가져오기
                    process_info = self._get_process_info(proc)
                    processes.append(process_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # 정렬
            if sort_by == "cpu_percent":
                processes.sort(key=lambda x: x.cpu_percent, reverse=(sort_order.lower() == "desc"))
            elif sort_by == "memory_percent":
                processes.sort(key=lambda x: x.memory_percent, reverse=(sort_order.lower() == "desc"))
            elif sort_by == "pid":
                processes.sort(key=lambda x: x.pid, reverse=(sort_order.lower() == "desc"))
            elif sort_by == "name":
                processes.sort(key=lambda x: x.name.lower(), reverse=(sort_order.lower() == "desc"))
            elif sort_by == "create_time":
                processes.sort(key=lambda x: x.create_time if x.create_time else "", reverse=(sort_order.lower() == "desc"))
            
            # 제한 적용
            if limit > 0:
                processes = processes[:limit]
            
            return processes
            
        except Exception as e:
            logger.error(f"프로세스 목록 가져오기 중 예외 발생: {e}")
            return []

    def get_process_by_pid(self, pid: int) -> ProcessInfo:
        """
        PID로 프로세스 정보를 가져옵니다.
        
        Args:
            pid: 프로세스 ID
            
        Returns:
            ProcessInfo: 프로세스 정보
        """
        try:
            proc = psutil.Process(pid)
            return self._get_process_info(proc)
        except psutil.NoSuchProcess:
            return ProcessInfo(
                pid=pid,
                name="",
                status="terminated",
                error=f"PID {pid}인 프로세스가 존재하지 않습니다"
            )
        except psutil.AccessDenied:
            return ProcessInfo(
                pid=pid,
                name="",
                status="access denied",
                error=f"PID {pid}인 프로세스 정보에 접근할 권한이 없습니다"
            )
        except Exception as e:
            logger.error(f"PID {pid}인 프로세스 정보 가져오기 중 예외 발생: {e}")
            return ProcessInfo(
                pid=pid,
                name="",
                status="error",
                error=f"프로세스 정보를 가져오는 중 오류 발생: {str(e)}"
            )

    def get_process_tree(self, pid: int = None) -> Dict[int, List[int]]:
        """
        프로세스 트리를 가져옵니다.
        
        Args:
            pid: 루트 프로세스 ID (None이면 모든 프로세스)
            
        Returns:
            Dict[int, List[int]]: 부모 PID를 키로, 자식 PID 목록을 값으로 하는 딕셔너리
        """
        try:
            # 프로세스 트리 구성
            tree = {}
            
            # 모든 프로세스 가져오기
            for proc in psutil.process_iter(['pid', 'ppid']):
                try:
                    proc_pid = proc.info['pid']
                    proc_ppid = proc.info.get('ppid', 0)
                    
                    # 특정 PID를 루트로 하는 경우
                    if pid is not None and proc_pid != pid and proc_ppid != pid:
                        continue
                    
                    # 부모 프로세스 ID가 트리에 없으면 추가
                    if proc_ppid not in tree:
                        tree[proc_ppid] = []
                    
                    # 자식 프로세스 추가
                    tree[proc_ppid].append(proc_pid)
                    
                    # 현재 프로세스 ID가 트리에 없으면 추가
                    if proc_pid not in tree:
                        tree[proc_pid] = []
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            return tree
            
        except Exception as e:
            logger.error(f"프로세스 트리 가져오기 중 예외 발생: {e}")
            return {}

    def get_system_info(self) -> SystemInfo:
        """
        시스템 정보를 가져옵니다.
        
        Returns:
            SystemInfo: 시스템 정보
        """
        try:
            system_info = SystemInfo()
            
            # CPU 정보
            system_info.cpu_count_physical = psutil.cpu_count(logical=False)
            system_info.cpu_count_logical = psutil.cpu_count(logical=True)
            system_info.cpu_percent = psutil.cpu_percent(interval=0.1)
            system_info.cpu_percent_per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            
            # 메모리 정보
            memory = psutil.virtual_memory()
            system_info.memory_total = memory.total
            system_info.memory_available = memory.available
            system_info.memory_used = memory.used
            system_info.memory_percent = memory.percent
            
            # 스왑 정보
            swap = psutil.swap_memory()
            system_info.swap_total = swap.total
            system_info.swap_used = swap.used
            system_info.swap_free = swap.free
            system_info.swap_percent = swap.percent
            
            # 디스크 사용량
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    system_info.disk_usage[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                        "fstype": partition.fstype,
                        "device": partition.device
                    }
                except (PermissionError, OSError):
                    # 일부 마운트 포인트는 접근할 수 없을 수 있음
                    continue
            
            # 부팅 시간
            boot_time = psutil.boot_time()
            system_info.boot_time = datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # 업타임 계산
            uptime_seconds = time.time() - boot_time
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            system_info.uptime = f"{int(days)}일 {int(hours)}시간 {int(minutes)}분 {int(seconds)}초"
            
            # 플랫폼 정보
            system_info.platform = platform.system()
            system_info.platform_version = platform.version()
            system_info.python_version = platform.python_version()
            system_info.hostname = platform.node()
            
            # 프로세스 및 스레드 수
            process_count = 0
            thread_count = 0
            for proc in psutil.process_iter(['pid', 'num_threads']):
                try:
                    process_count += 1
                    thread_count += proc.info['num_threads'] if 'num_threads' in proc.info else 0
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            system_info.process_count = process_count
            system_info.thread_count = thread_count
            
            return system_info
            
        except Exception as e:
            logger.error(f"시스템 정보 가져오기 중 예외 발생: {e}")
            system_info = SystemInfo()
            system_info.error = f"시스템 정보를 가져오는 중 오류 발생: {str(e)}"
            return system_info

    def kill_process(self, pid: int) -> bool:
        """
        프로세스를 종료합니다.
        
        Args:
            pid: 종료할 프로세스 ID
            
        Returns:
            bool: 성공 여부
        """
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            
            # 프로세스가 종료될 때까지 대기 (최대 3초)
            gone, alive = psutil.wait_procs([proc], timeout=3)
            
            # 여전히 살아있으면 강제 종료
            if alive:
                for p in alive:
                    p.kill()
            
            return True
        except psutil.NoSuchProcess:
            logger.error(f"PID {pid}인 프로세스가 존재하지 않습니다")
            return False
        except psutil.AccessDenied:
            logger.error(f"PID {pid}인 프로세스를 종료할 권한이 없습니다")
            return False
        except Exception as e:
            logger.error(f"PID {pid}인 프로세스 종료 중 예외 발생: {e}")
            return False

    def get_process_by_name(self, name: str, case_sensitive: bool = False) -> List[ProcessInfo]:
        """
        이름으로 프로세스 정보를 가져옵니다.
        
        Args:
            name: 프로세스 이름
            case_sensitive: 대소문자 구분 여부
            
        Returns:
            List[ProcessInfo]: 프로세스 정보 목록
        """
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name']
                    
                    # 이름 비교
                    if case_sensitive:
                        if name == proc_name:
                            processes.append(self._get_process_info(proc))
                    else:
                        if name.lower() in proc_name.lower():
                            processes.append(self._get_process_info(proc))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            return processes
            
        except Exception as e:
            logger.error(f"이름으로 프로세스 정보 가져오기 중 예외 발생: {e}")
            return []

    def get_top_processes(self, resource_type: str = "cpu", limit: int = 10) -> List[ProcessInfo]:
        """
        리소스 사용량이 가장 높은 프로세스 목록을 가져옵니다.
        
        Args:
            resource_type: 리소스 유형 (cpu 또는 memory)
            limit: 반환할 프로세스 수
            
        Returns:
            List[ProcessInfo]: 프로세스 정보 목록
        """
        try:
            # 모든 프로세스 가져오기
            processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # 프로세스 정보 가져오기
                    process_info = self._get_process_info(proc)
                    processes.append(process_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # 리소스 유형에 따라 정렬
            if resource_type.lower() == "cpu":
                processes.sort(key=lambda x: x.cpu_percent, reverse=True)
            else:  # memory
                processes.sort(key=lambda x: x.memory_percent, reverse=True)
            
            # 제한 적용
            return processes[:limit]
            
        except Exception as e:
            logger.error(f"리소스 사용량이 높은 프로세스 가져오기 중 예외 발생: {e}")
            return []


# 싱글톤 인스턴스 생성
process_monitor = ProcessMonitoringService()


@app.tool()
def get_process_list(limit: int = DEFAULT_PROCESS_LIMIT, sort_by: str = DEFAULT_SORT_BY, 
                     sort_order: str = DEFAULT_SORT_ORDER, name_filter: str = None, 
                     username_filter: str = None, status_filter: str = None) -> dict:
    """
    프로세스 목록을 가져옵니다.
    
    Args:
        limit: 반환할 프로세스 수 제한 (기본값: 50)
        sort_by: 정렬 기준 (cpu_percent, memory_percent, pid, name, create_time) (기본값: cpu_percent)
        sort_order: 정렬 순서 (asc, desc) (기본값: desc)
        name_filter: 프로세스 이름 필터
        username_filter: 사용자 이름 필터
        status_filter: 상태 필터 (running, sleeping, disk-sleep, stopped, zombie, dead)
        
    Returns:
        dict: 프로세스 목록을 포함한 딕셔너리
    """
    try:
        processes = process_monitor.get_process_list(limit, sort_by, sort_order, name_filter, username_filter, status_filter)
        return {
            "result": [process.__dict__ for process in processes]
        }
    except Exception as e:
        logger.error(f"프로세스 목록 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"프로세스 목록 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_process_by_pid(pid: int) -> dict:
    """
    PID로 프로세스 정보를 가져옵니다.
    
    Args:
        pid: 프로세스 ID
        
    Returns:
        dict: 프로세스 정보를 포함한 딕셔너리
    """
    try:
        process = process_monitor.get_process_by_pid(pid)
        return {
            "result": process.__dict__
        }
    except Exception as e:
        logger.error(f"PID {pid}인 프로세스 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"프로세스 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_process_tree(pid: int = None) -> dict:
    """
    프로세스 트리를 가져옵니다.
    
    Args:
        pid: 루트 프로세스 ID (None이면 모든 프로세스)
        
    Returns:
        dict: 프로세스 트리를 포함한 딕셔너리
    """
    try:
        tree = process_monitor.get_process_tree(pid)
        return {
            "result": tree
        }
    except Exception as e:
        logger.error(f"프로세스 트리 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"프로세스 트리 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_system_info() -> dict:
    """
    시스템 정보를 가져옵니다.
    
    Returns:
        dict: 시스템 정보를 포함한 딕셔너리
    """
    try:
        system_info = process_monitor.get_system_info()
        return {
            "result": system_info.__dict__
        }
    except Exception as e:
        logger.error(f"시스템 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"시스템 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def kill_process(pid: int) -> dict:
    """
    프로세스를 종료합니다.
    
    Args:
        pid: 종료할 프로세스 ID
        
    Returns:
        dict: 종료 결과를 포함한 딕셔너리
    """
    try:
        success = process_monitor.kill_process(pid)
        if success:
            return {
                "result": {
                    "success": True,
                    "message": f"PID {pid}인 프로세스가 성공적으로 종료되었습니다"
                }
            }
        else:
            return {
                "result": {
                    "success": False,
                    "message": f"PID {pid}인 프로세스 종료에 실패했습니다"
                }
            }
    except Exception as e:
        logger.error(f"프로세스 종료 중 오류 발생: {str(e)}")
        return {"error": f"프로세스 종료 중 오류 발생: {str(e)}"}


@app.tool()
def get_process_by_name(name: str, case_sensitive: bool = False) -> dict:
    """
    이름으로 프로세스 정보를 가져옵니다.
    
    Args:
        name: 프로세스 이름
        case_sensitive: 대소문자 구분 여부 (기본값: False)
        
    Returns:
        dict: 프로세스 정보 목록을 포함한 딕셔너리
    """
    try:
        processes = process_monitor.get_process_by_name(name, case_sensitive)
        return {
            "result": [process.__dict__ for process in processes]
        }
    except Exception as e:
        logger.error(f"이름으로 프로세스 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"프로세스 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_top_processes(resource_type: str = "cpu", limit: int = 10) -> dict:
    """
    리소스 사용량이 가장 높은 프로세스 목록을 가져옵니다.
    
    Args:
        resource_type: 리소스 유형 (cpu 또는 memory) (기본값: cpu)
        limit: 반환할 프로세스 수 (기본값: 10)
        
    Returns:
        dict: 프로세스 정보 목록을 포함한 딕셔너리
    """
    try:
        processes = process_monitor.get_top_processes(resource_type, limit)
        return {
            "result": [process.__dict__ for process in processes]
        }
    except Exception as e:
        logger.error(f"리소스 사용량이 높은 프로세스 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"프로세스 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    프로세스 모니터링 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Process Monitoring Tool",
                "description": "현재 사용중인 OS의 프로세스 현황을 조회하는 도구",
                "tools": [
                    {"name": "get_process_list", "description": "프로세스 목록을 가져옵니다"},
                    {"name": "get_process_by_pid", "description": "PID로 프로세스 정보를 가져옵니다"},
                    {"name": "get_process_tree", "description": "프로세스 트리를 가져옵니다"},
                    {"name": "get_system_info", "description": "시스템 정보를 가져옵니다"},
                    {"name": "kill_process", "description": "프로세스를 종료합니다"},
                    {"name": "get_process_by_name", "description": "이름으로 프로세스 정보를 가져옵니다"},
                    {"name": "get_top_processes", "description": "리소스 사용량이 가장 높은 프로세스 목록을 가져옵니다"}
                ],
                "usage_examples": [
                    {"command": "get_process_list()", "description": "모든 프로세스 목록 가져오기"},
                    {"command": "get_process_by_pid(1234)", "description": "PID 1234인 프로세스 정보 가져오기"},
                    {"command": "get_top_processes(resource_type='cpu', limit=5)", "description": "CPU 사용량이 가장 높은 5개 프로세스 가져오기"},
                    {"command": "get_process_by_name('chrome')", "description": "'chrome'이 포함된 이름의 프로세스 가져오기"},
                    {"command": "get_system_info()", "description": "시스템 정보 가져오기"}
                ],
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "psutil_version": psutil.__version__
            }
        }
        
    except Exception as e:
        return {"error": f"도구 정보를 가져오는 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    try:
        logger.info("FastMCP app.run() 호출 시작...")
        app.run(transport=TRANSPORT)
        logger.info("FastMCP app.run() 정상 종료.")
    except Exception as e:
        logger.error("process_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise