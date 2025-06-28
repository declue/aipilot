#!/usr/bin/env python3
"""
Kubernetes API MCP Server
Kubernetes API를 통해 클러스터 상황, pod 현황, 로그 조회, 이벤트 조회 등 다양한 observability 기능을 제공합니다.
LLM을 통한 Kubernetes의 다양한 기능을 활용할 수 있는 도구입니다.
"""

import logging
import os
import sys
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from mcp.server.fastmcp import FastMCP

# --- 디버깅 로깅 설정 ---
# 이 스크립트가 별도 프로세스로 실행될 때의 오류를 추적하기 위함
# 프로젝트 루트에 kubernetes_tool_mcp.log 파일 생성
log_file_path = Path(__file__).resolve().parents[2] / "kubernetes_tool_mcp.log"
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# 환경 변수로 로그 레벨 제어 (기본값: WARNING)
log_level = os.getenv("KUBERNETES_TOOL_LOG_LEVEL", "WARNING").upper()
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
    logger.info("Kubernetes Tool MCP 서버 프로세스 시작 (PID: %s)", os.getpid())
    logger.info("Python Executable: %s", sys.executable)
    logger.info("sys.path: %s", sys.path)
# --- 로깅 설정 끝 ---

# Create MCP Server
app = FastMCP(
    title="Kubernetes API Server",
    description="A server for Kubernetes API operations",
    version="1.0.0",
)

TRANSPORT = "stdio"

# 기본 설정
KUBECONFIG_PATH = os.getenv("KUBECONFIG", "~/.kube/config")


@dataclass
class KubernetesCluster:
    """Kubernetes 클러스터 정보를 담는 데이터 클래스"""
    name: str
    version: str
    platform: str = ""
    nodes_count: int = 0
    pods_count: int = 0
    namespaces_count: int = 0


@dataclass
class KubernetesNode:
    """Kubernetes 노드 정보를 담는 데이터 클래스"""
    name: str
    status: str
    roles: List[str] = field(default_factory=list)
    version: str = ""
    internal_ip: str = ""
    external_ip: str = ""
    os_image: str = ""
    kernel_version: str = ""
    container_runtime: str = ""
    cpu_capacity: str = ""
    memory_capacity: str = ""
    cpu_allocatable: str = ""
    memory_allocatable: str = ""
    cpu_usage: str = ""
    memory_usage: str = ""
    pods_count: int = 0
    conditions: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class KubernetesPod:
    """Kubernetes Pod 정보를 담는 데이터 클래스"""
    name: str
    namespace: str
    status: str
    node: str = ""
    ip: str = ""
    containers: List[str] = field(default_factory=list)
    restart_count: int = 0
    age: str = ""
    created_at: str = ""
    conditions: Dict[str, str] = field(default_factory=dict)


@dataclass
class KubernetesService:
    """Kubernetes Service 정보를 담는 데이터 클래스"""
    name: str
    namespace: str
    type: str
    cluster_ip: str = ""
    external_ip: str = ""
    ports: List[Dict[str, Any]] = field(default_factory=list)
    selector: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class KubernetesDeployment:
    """Kubernetes Deployment 정보를 담는 데이터 클래스"""
    name: str
    namespace: str
    replicas: int
    available_replicas: int
    ready_replicas: int
    updated_replicas: int
    strategy: str = ""
    selector: Dict[str, str] = field(default_factory=dict)
    containers: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""


@dataclass
class KubernetesEvent:
    """Kubernetes Event 정보를 담는 데이터 클래스"""
    name: str
    namespace: str
    type: str
    reason: str
    message: str
    source: str = ""
    object_kind: str = ""
    object_name: str = ""
    count: int = 1
    first_timestamp: str = ""
    last_timestamp: str = ""


class KubernetesAPIService:
    """Kubernetes API 서비스 클래스"""

    def __init__(self, kubeconfig_path: str = None):
        """
        Kubernetes API 서비스 초기화
        
        Args:
            kubeconfig_path: kubeconfig 파일 경로 (없으면 환경 변수에서 가져옴)
        """
        self.kubeconfig_path = kubeconfig_path or os.path.expanduser(KUBECONFIG_PATH)
        
        try:
            # kubeconfig 파일이 존재하는 경우 해당 파일로 설정
            if os.path.exists(self.kubeconfig_path):
                config.load_kube_config(config_file=self.kubeconfig_path)
                logger.info(f"kubeconfig 파일 로드 성공: {self.kubeconfig_path}")
            else:
                # 클러스터 내부에서 실행 중인 경우 (Pod 내부)
                config.load_incluster_config()
                logger.info("클러스터 내부 설정 로드 성공")
            
            # API 클라이언트 초기화
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.batch_v1 = client.BatchV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            self.version_api = client.VersionApi()
            
            # 연결 테스트
            self.version_api.get_code()
            logger.info("Kubernetes API 연결 성공")
            
        except Exception as e:
            logger.error(f"Kubernetes API 초기화 중 오류 발생: {e}")
            raise

    def get_cluster_info(self) -> KubernetesCluster:
        """
        클러스터 정보를 가져옵니다.
        
        Returns:
            KubernetesCluster: 클러스터 정보
        """
        try:
            # 버전 정보 가져오기
            version_info = self.version_api.get_code()
            
            # 노드 수 가져오기
            nodes = self.core_v1.list_node()
            nodes_count = len(nodes.items)
            
            # 파드 수 가져오기
            pods = self.core_v1.list_pod_for_all_namespaces(limit=1000)
            pods_count = len(pods.items)
            
            # 네임스페이스 수 가져오기
            namespaces = self.core_v1.list_namespace()
            namespaces_count = len(namespaces.items)
            
            return KubernetesCluster(
                name="kubernetes",
                version=version_info.git_version,
                platform=version_info.platform,
                nodes_count=nodes_count,
                pods_count=pods_count,
                namespaces_count=namespaces_count
            )
            
        except ApiException as e:
            logger.error(f"클러스터 정보 가져오기 중 API 오류 발생: {e}")
            raise
        except Exception as e:
            logger.error(f"클러스터 정보 가져오기 중 오류 발생: {e}")
            raise

    def get_nodes(self) -> List[KubernetesNode]:
        """
        모든 노드 정보를 가져옵니다.
        
        Returns:
            List[KubernetesNode]: 노드 목록
        """
        try:
            nodes_list = self.core_v1.list_node()
            result = []
            
            for node in nodes_list.items:
                # 노드 기본 정보
                name = node.metadata.name
                status = "Ready"
                roles = []
                
                # 노드 상태 확인
                if node.status.conditions:
                    for condition in node.status.conditions:
                        if condition.type == "Ready":
                            status = "Ready" if condition.status == "True" else "NotReady"
                
                # 노드 역할 확인
                if node.metadata.labels:
                    for key, value in node.metadata.labels.items():
                        if key.startswith("node-role.kubernetes.io/"):
                            role = key.split("/")[1]
                            roles.append(role)
                
                # 노드 IP 주소 확인
                internal_ip = ""
                external_ip = ""
                if node.status.addresses:
                    for address in node.status.addresses:
                        if address.type == "InternalIP":
                            internal_ip = address.address
                        elif address.type == "ExternalIP":
                            external_ip = address.address
                
                # 노드 시스템 정보
                os_image = node.status.node_info.os_image if node.status.node_info else ""
                kernel_version = node.status.node_info.kernel_version if node.status.node_info else ""
                container_runtime = node.status.node_info.container_runtime_version if node.status.node_info else ""
                kube_version = node.status.node_info.kubelet_version if node.status.node_info else ""
                
                # 노드 리소스 정보
                cpu_capacity = node.status.capacity.get("cpu", "")
                memory_capacity = node.status.capacity.get("memory", "")
                cpu_allocatable = node.status.allocatable.get("cpu", "")
                memory_allocatable = node.status.allocatable.get("memory", "")
                
                # 노드 컨디션 정보
                conditions = {}
                if node.status.conditions:
                    for condition in node.status.conditions:
                        conditions[condition.type] = condition.status
                
                # 노드에서 실행 중인 파드 수 계산
                field_selector = f"spec.nodeName={name},status.phase!=Failed,status.phase!=Succeeded"
                pods = self.core_v1.list_pod_for_all_namespaces(field_selector=field_selector)
                pods_count = len(pods.items)
                
                # 생성 시간
                created_at = node.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S") if node.metadata.creation_timestamp else ""
                
                node_info = KubernetesNode(
                    name=name,
                    status=status,
                    roles=roles,
                    version=kube_version,
                    internal_ip=internal_ip,
                    external_ip=external_ip,
                    os_image=os_image,
                    kernel_version=kernel_version,
                    container_runtime=container_runtime,
                    cpu_capacity=cpu_capacity,
                    memory_capacity=memory_capacity,
                    cpu_allocatable=cpu_allocatable,
                    memory_allocatable=memory_allocatable,
                    pods_count=pods_count,
                    conditions=conditions,
                    created_at=created_at
                )
                
                result.append(node_info)
            
            return result
            
        except ApiException as e:
            logger.error(f"노드 정보 가져오기 중 API 오류 발생: {e}")
            raise
        except Exception as e:
            logger.error(f"노드 정보 가져오기 중 오류 발생: {e}")
            raise

    def get_pods(self, namespace: str = None, label_selector: str = None, field_selector: str = None) -> List[KubernetesPod]:
        """
        파드 목록을 가져옵니다.
        
        Args:
            namespace: 네임스페이스 (None이면 모든 네임스페이스)
            label_selector: 레이블 셀렉터 (예: "app=nginx")
            field_selector: 필드 셀렉터 (예: "status.phase=Running")
            
        Returns:
            List[KubernetesPod]: 파드 목록
        """
        try:
            if namespace:
                pods_list = self.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector
                )
            else:
                pods_list = self.core_v1.list_pod_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector
                )
            
            result = []
            
            for pod in pods_list.items:
                # 파드 기본 정보
                name = pod.metadata.name
                pod_namespace = pod.metadata.namespace
                
                # 파드 상태 확인
                status = pod.status.phase
                if status == "Running":
                    # 컨테이너 상태 확인
                    if pod.status.container_statuses:
                        for container_status in pod.status.container_statuses:
                            if not container_status.ready:
                                status = "NotReady"
                                break
                
                # 파드가 실행 중인 노드
                node = pod.spec.node_name if pod.spec else ""
                
                # 파드 IP
                ip = pod.status.pod_ip if pod.status else ""
                
                # 컨테이너 목록
                containers = []
                if pod.spec and pod.spec.containers:
                    for container in pod.spec.containers:
                        containers.append(container.name)
                
                # 재시작 횟수
                restart_count = 0
                if pod.status.container_statuses:
                    for container_status in pod.status.container_statuses:
                        restart_count += container_status.restart_count
                
                # 생성 시간 및 나이
                created_at = ""
                age = ""
                if pod.metadata.creation_timestamp:
                    created_at = pod.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    age_seconds = (datetime.now(pod.metadata.creation_timestamp.tzinfo) - pod.metadata.creation_timestamp).total_seconds()
                    
                    if age_seconds < 60:
                        age = f"{int(age_seconds)}s"
                    elif age_seconds < 3600:
                        age = f"{int(age_seconds / 60)}m"
                    elif age_seconds < 86400:
                        age = f"{int(age_seconds / 3600)}h"
                    else:
                        age = f"{int(age_seconds / 86400)}d"
                
                # 파드 컨디션
                conditions = {}
                if pod.status.conditions:
                    for condition in pod.status.conditions:
                        conditions[condition.type] = condition.status
                
                pod_info = KubernetesPod(
                    name=name,
                    namespace=pod_namespace,
                    status=status,
                    node=node,
                    ip=ip,
                    containers=containers,
                    restart_count=restart_count,
                    age=age,
                    created_at=created_at,
                    conditions=conditions
                )
                
                result.append(pod_info)
            
            return result
            
        except ApiException as e:
            logger.error(f"파드 정보 가져오기 중 API 오류 발생: {e}")
            raise
        except Exception as e:
            logger.error(f"파드 정보 가져오기 중 오류 발생: {e}")
            raise

    def get_pod_logs(self, name: str, namespace: str, container: str = None, tail_lines: int = None, previous: bool = False) -> str:
        """
        파드 로그를 가져옵니다.
        
        Args:
            name: 파드 이름
            namespace: 네임스페이스
            container: 컨테이너 이름 (None이면 첫 번째 컨테이너)
            tail_lines: 가져올 로그 라인 수 (None이면 모든 로그)
            previous: 이전 컨테이너의 로그 가져오기 여부
            
        Returns:
            str: 파드 로그
        """
        try:
            # 컨테이너 이름이 지정되지 않은 경우 파드의 첫 번째 컨테이너 사용
            if not container:
                pod = self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
                if pod.spec.containers and len(pod.spec.containers) > 0:
                    container = pod.spec.containers[0].name
            
            # 로그 가져오기
            logs = self.core_v1.read_namespaced_pod_log(
                name=name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
                previous=previous
            )
            
            return logs
            
        except ApiException as e:
            logger.error(f"파드 로그 가져오기 중 API 오류 발생: {e}")
            if e.status == 404:
                return f"파드를 찾을 수 없습니다: {namespace}/{name}"
            raise
        except Exception as e:
            logger.error(f"파드 로그 가져오기 중 오류 발생: {e}")
            raise

    def get_services(self, namespace: str = None, label_selector: str = None) -> List[KubernetesService]:
        """
        서비스 목록을 가져옵니다.
        
        Args:
            namespace: 네임스페이스 (None이면 모든 네임스페이스)
            label_selector: 레이블 셀렉터 (예: "app=nginx")
            
        Returns:
            List[KubernetesService]: 서비스 목록
        """
        try:
            if namespace:
                services_list = self.core_v1.list_namespaced_service(
                    namespace=namespace,
                    label_selector=label_selector
                )
            else:
                services_list = self.core_v1.list_service_for_all_namespaces(
                    label_selector=label_selector
                )
            
            result = []
            
            for svc in services_list.items:
                # 서비스 기본 정보
                name = svc.metadata.name
                svc_namespace = svc.metadata.namespace
                svc_type = svc.spec.type
                
                # IP 주소
                cluster_ip = svc.spec.cluster_ip
                external_ip = ""
                
                if svc.status and svc.status.load_balancer and svc.status.load_balancer.ingress:
                    for ingress in svc.status.load_balancer.ingress:
                        if ingress.ip:
                            external_ip = ingress.ip
                        elif ingress.hostname:
                            external_ip = ingress.hostname
                
                # 포트 정보
                ports = []
                if svc.spec.ports:
                    for port in svc.spec.ports:
                        port_info = {
                            "name": port.name,
                            "port": port.port,
                            "target_port": port.target_port,
                            "protocol": port.protocol
                        }
                        if port.node_port:
                            port_info["node_port"] = port.node_port
                        ports.append(port_info)
                
                # 셀렉터
                selector = svc.spec.selector if svc.spec.selector else {}
                
                # 생성 시간
                created_at = svc.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S") if svc.metadata.creation_timestamp else ""
                
                service_info = KubernetesService(
                    name=name,
                    namespace=svc_namespace,
                    type=svc_type,
                    cluster_ip=cluster_ip,
                    external_ip=external_ip,
                    ports=ports,
                    selector=selector,
                    created_at=created_at
                )
                
                result.append(service_info)
            
            return result
            
        except ApiException as e:
            logger.error(f"서비스 정보 가져오기 중 API 오류 발생: {e}")
            raise
        except Exception as e:
            logger.error(f"서비스 정보 가져오기 중 오류 발생: {e}")
            raise

    def get_deployments(self, namespace: str = None, label_selector: str = None) -> List[KubernetesDeployment]:
        """
        디플로이먼트 목록을 가져옵니다.
        
        Args:
            namespace: 네임스페이스 (None이면 모든 네임스페이스)
            label_selector: 레이블 셀렉터 (예: "app=nginx")
            
        Returns:
            List[KubernetesDeployment]: 디플로이먼트 목록
        """
        try:
            if namespace:
                deployments_list = self.apps_v1.list_namespaced_deployment(
                    namespace=namespace,
                    label_selector=label_selector
                )
            else:
                deployments_list = self.apps_v1.list_deployment_for_all_namespaces(
                    label_selector=label_selector
                )
            
            result = []
            
            for deploy in deployments_list.items:
                # 디플로이먼트 기본 정보
                name = deploy.metadata.name
                deploy_namespace = deploy.metadata.namespace
                
                # 레플리카 정보
                replicas = deploy.spec.replicas if deploy.spec else 0
                available_replicas = deploy.status.available_replicas if deploy.status and deploy.status.available_replicas else 0
                ready_replicas = deploy.status.ready_replicas if deploy.status and deploy.status.ready_replicas else 0
                updated_replicas = deploy.status.updated_replicas if deploy.status and deploy.status.updated_replicas else 0
                
                # 배포 전략
                strategy = deploy.spec.strategy.type if deploy.spec and deploy.spec.strategy else ""
                
                # 셀렉터
                selector = {}
                if deploy.spec and deploy.spec.selector and deploy.spec.selector.match_labels:
                    selector = deploy.spec.selector.match_labels
                
                # 컨테이너 정보
                containers = []
                if deploy.spec and deploy.spec.template and deploy.spec.template.spec and deploy.spec.template.spec.containers:
                    for container in deploy.spec.template.spec.containers:
                        container_info = {
                            "name": container.name,
                            "image": container.image,
                            "ports": []
                        }
                        
                        if container.ports:
                            for port in container.ports:
                                port_info = {
                                    "container_port": port.container_port,
                                    "protocol": port.protocol
                                }
                                container_info["ports"].append(port_info)
                        
                        containers.append(container_info)
                
                # 생성 시간
                created_at = deploy.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S") if deploy.metadata.creation_timestamp else ""
                
                deployment_info = KubernetesDeployment(
                    name=name,
                    namespace=deploy_namespace,
                    replicas=replicas,
                    available_replicas=available_replicas,
                    ready_replicas=ready_replicas,
                    updated_replicas=updated_replicas,
                    strategy=strategy,
                    selector=selector,
                    containers=containers,
                    created_at=created_at
                )
                
                result.append(deployment_info)
            
            return result
            
        except ApiException as e:
            logger.error(f"디플로이먼트 정보 가져오기 중 API 오류 발생: {e}")
            raise
        except Exception as e:
            logger.error(f"디플로이먼트 정보 가져오기 중 오류 발생: {e}")
            raise

    def get_events(self, namespace: str = None, field_selector: str = None, sort_by: str = "lastTimestamp") -> List[KubernetesEvent]:
        """
        이벤트 목록을 가져옵니다.
        
        Args:
            namespace: 네임스페이스 (None이면 모든 네임스페이스)
            field_selector: 필드 셀렉터 (예: "involvedObject.name=nginx")
            sort_by: 정렬 기준 (lastTimestamp 또는 firstTimestamp)
            
        Returns:
            List[KubernetesEvent]: 이벤트 목록
        """
        try:
            if namespace:
                events_list = self.core_v1.list_namespaced_event(
                    namespace=namespace,
                    field_selector=field_selector
                )
            else:
                events_list = self.core_v1.list_event_for_all_namespaces(
                    field_selector=field_selector
                )
            
            result = []
            
            for event in events_list.items:
                # 이벤트 기본 정보
                name = event.metadata.name
                event_namespace = event.metadata.namespace
                event_type = event.type
                reason = event.reason
                message = event.message
                
                # 소스 정보
                source = ""
                if event.source:
                    if event.source.component:
                        source = event.source.component
                    if event.source.host:
                        source += f" on {event.source.host}"
                
                # 관련 객체 정보
                object_kind = ""
                object_name = ""
                if event.involved_object:
                    object_kind = event.involved_object.kind
                    object_name = event.involved_object.name
                
                # 발생 횟수
                count = event.count if event.count else 1
                
                # 타임스탬프
                first_timestamp = ""
                last_timestamp = ""
                if event.first_timestamp:
                    first_timestamp = event.first_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                if event.last_timestamp:
                    last_timestamp = event.last_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                event_info = KubernetesEvent(
                    name=name,
                    namespace=event_namespace,
                    type=event_type,
                    reason=reason,
                    message=message,
                    source=source,
                    object_kind=object_kind,
                    object_name=object_name,
                    count=count,
                    first_timestamp=first_timestamp,
                    last_timestamp=last_timestamp
                )
                
                result.append(event_info)
            
            # 이벤트 정렬
            if sort_by == "lastTimestamp":
                result.sort(key=lambda x: x.last_timestamp if x.last_timestamp else "", reverse=True)
            elif sort_by == "firstTimestamp":
                result.sort(key=lambda x: x.first_timestamp if x.first_timestamp else "", reverse=True)
            
            return result
            
        except ApiException as e:
            logger.error(f"이벤트 정보 가져오기 중 API 오류 발생: {e}")
            raise
        except Exception as e:
            logger.error(f"이벤트 정보 가져오기 중 오류 발생: {e}")
            raise

    def get_namespaces(self) -> List[Dict[str, Any]]:
        """
        네임스페이스 목록을 가져옵니다.
        
        Returns:
            List[Dict[str, Any]]: 네임스페이스 목록
        """
        try:
            namespaces_list = self.core_v1.list_namespace()
            result = []
            
            for ns in namespaces_list.items:
                # 네임스페이스 기본 정보
                name = ns.metadata.name
                status = ns.status.phase if ns.status else ""
                
                # 생성 시간
                created_at = ns.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S") if ns.metadata.creation_timestamp else ""
                
                # 레이블
                labels = ns.metadata.labels if ns.metadata.labels else {}
                
                namespace_info = {
                    "name": name,
                    "status": status,
                    "created_at": created_at,
                    "labels": labels
                }
                
                result.append(namespace_info)
            
            return result
            
        except ApiException as e:
            logger.error(f"네임스페이스 정보 가져오기 중 API 오류 발생: {e}")
            raise
        except Exception as e:
            logger.error(f"네임스페이스 정보 가져오기 중 오류 발생: {e}")
            raise

    def describe_pod(self, name: str, namespace: str) -> Dict[str, Any]:
        """
        파드 상세 정보를 가져옵니다.
        
        Args:
            name: 파드 이름
            namespace: 네임스페이스
            
        Returns:
            Dict[str, Any]: 파드 상세 정보
        """
        try:
            pod = self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
            
            # 기본 정보
            result = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "uid": pod.metadata.uid,
                "creation_timestamp": pod.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S") if pod.metadata.creation_timestamp else "",
                "labels": pod.metadata.labels if pod.metadata.labels else {},
                "annotations": pod.metadata.annotations if pod.metadata.annotations else {},
                "status": {
                    "phase": pod.status.phase,
                    "pod_ip": pod.status.pod_ip,
                    "host_ip": pod.status.host_ip,
                    "qos_class": pod.status.qos_class,
                    "start_time": pod.status.start_time.strftime("%Y-%m-%d %H:%M:%S") if pod.status.start_time else "",
                },
                "spec": {
                    "node_name": pod.spec.node_name,
                    "service_account": pod.spec.service_account_name,
                    "restart_policy": pod.spec.restart_policy,
                    "termination_grace_period_seconds": pod.spec.termination_grace_period_seconds,
                    "dns_policy": pod.spec.dns_policy,
                }
            }
            
            # 컨테이너 정보
            containers = []
            if pod.spec.containers:
                for container in pod.spec.containers:
                    container_info = {
                        "name": container.name,
                        "image": container.image,
                        "image_pull_policy": container.image_pull_policy,
                        "ports": [],
                        "environment": [],
                        "volume_mounts": [],
                        "resources": {}
                    }
                    
                    # 포트 정보
                    if container.ports:
                        for port in container.ports:
                            port_info = {
                                "name": port.name,
                                "container_port": port.container_port,
                                "protocol": port.protocol
                            }
                            if port.host_port:
                                port_info["host_port"] = port.host_port
                            container_info["ports"].append(port_info)
                    
                    # 환경 변수
                    if container.env:
                        for env in container.env:
                            env_info = {"name": env.name}
                            if env.value:
                                env_info["value"] = env.value
                            elif env.value_from:
                                env_info["value_from"] = {}
                                if env.value_from.config_map_key_ref:
                                    env_info["value_from"]["config_map_key_ref"] = {
                                        "name": env.value_from.config_map_key_ref.name,
                                        "key": env.value_from.config_map_key_ref.key
                                    }
                                elif env.value_from.secret_key_ref:
                                    env_info["value_from"]["secret_key_ref"] = {
                                        "name": env.value_from.secret_key_ref.name,
                                        "key": env.value_from.secret_key_ref.key
                                    }
                                elif env.value_from.field_ref:
                                    env_info["value_from"]["field_ref"] = {
                                        "field_path": env.value_from.field_ref.field_path
                                    }
                            container_info["environment"].append(env_info)
                    
                    # 볼륨 마운트
                    if container.volume_mounts:
                        for mount in container.volume_mounts:
                            mount_info = {
                                "name": mount.name,
                                "mount_path": mount.mount_path,
                                "read_only": mount.read_only
                            }
                            container_info["volume_mounts"].append(mount_info)
                    
                    # 리소스 요청 및 제한
                    if container.resources:
                        if container.resources.requests:
                            container_info["resources"]["requests"] = container.resources.requests
                        if container.resources.limits:
                            container_info["resources"]["limits"] = container.resources.limits
                    
                    containers.append(container_info)
            
            result["containers"] = containers
            
            # 컨테이너 상태
            container_statuses = []
            if pod.status.container_statuses:
                for status in pod.status.container_statuses:
                    status_info = {
                        "name": status.name,
                        "ready": status.ready,
                        "restart_count": status.restart_count,
                        "image": status.image,
                        "image_id": status.image_id,
                        "container_id": status.container_id,
                        "state": {}
                    }
                    
                    # 컨테이너 상태 (running, waiting, terminated)
                    if status.state:
                        if status.state.running:
                            status_info["state"]["running"] = {
                                "started_at": status.state.running.started_at.strftime("%Y-%m-%d %H:%M:%S") if status.state.running.started_at else ""
                            }
                        elif status.state.waiting:
                            status_info["state"]["waiting"] = {
                                "reason": status.state.waiting.reason,
                                "message": status.state.waiting.message
                            }
                        elif status.state.terminated:
                            status_info["state"]["terminated"] = {
                                "exit_code": status.state.terminated.exit_code,
                                "reason": status.state.terminated.reason,
                                "message": status.state.terminated.message,
                                "started_at": status.state.terminated.started_at.strftime("%Y-%m-%d %H:%M:%S") if status.state.terminated.started_at else "",
                                "finished_at": status.state.terminated.finished_at.strftime("%Y-%m-%d %H:%M:%S") if status.state.terminated.finished_at else ""
                            }
                    
                    container_statuses.append(status_info)
            
            result["container_statuses"] = container_statuses
            
            # 컨디션
            conditions = []
            if pod.status.conditions:
                for condition in pod.status.conditions:
                    condition_info = {
                        "type": condition.type,
                        "status": condition.status,
                        "reason": condition.reason,
                        "message": condition.message,
                        "last_transition_time": condition.last_transition_time.strftime("%Y-%m-%d %H:%M:%S") if condition.last_transition_time else ""
                    }
                    conditions.append(condition_info)
            
            result["conditions"] = conditions
            
            # 볼륨
            volumes = []
            if pod.spec.volumes:
                for volume in pod.spec.volumes:
                    volume_info = {
                        "name": volume.name,
                        "type": ""
                    }
                    
                    # 볼륨 타입 및 세부 정보
                    if volume.config_map:
                        volume_info["type"] = "ConfigMap"
                        volume_info["config_map"] = {
                            "name": volume.config_map.name,
                            "items": []
                        }
                        if volume.config_map.items:
                            for item in volume.config_map.items:
                                volume_info["config_map"]["items"].append({
                                    "key": item.key,
                                    "path": item.path
                                })
                    elif volume.secret:
                        volume_info["type"] = "Secret"
                        volume_info["secret"] = {
                            "secret_name": volume.secret.secret_name,
                            "items": []
                        }
                        if volume.secret.items:
                            for item in volume.secret.items:
                                volume_info["secret"]["items"].append({
                                    "key": item.key,
                                    "path": item.path
                                })
                    elif volume.persistent_volume_claim:
                        volume_info["type"] = "PersistentVolumeClaim"
                        volume_info["persistent_volume_claim"] = {
                            "claim_name": volume.persistent_volume_claim.claim_name,
                            "read_only": volume.persistent_volume_claim.read_only
                        }
                    elif volume.host_path:
                        volume_info["type"] = "HostPath"
                        volume_info["host_path"] = {
                            "path": volume.host_path.path,
                            "type": volume.host_path.type
                        }
                    elif volume.empty_dir:
                        volume_info["type"] = "EmptyDir"
                        volume_info["empty_dir"] = {}
                        if volume.empty_dir.medium:
                            volume_info["empty_dir"]["medium"] = volume.empty_dir.medium
                        if volume.empty_dir.size_limit:
                            volume_info["empty_dir"]["size_limit"] = volume.empty_dir.size_limit
                    
                    volumes.append(volume_info)
            
            result["volumes"] = volumes
            
            # 이벤트 정보
            field_selector = f"involvedObject.name={name},involvedObject.namespace={namespace}"
            events = self.get_events(namespace=namespace, field_selector=field_selector)
            result["events"] = [event.__dict__ for event in events]
            
            return result
            
        except ApiException as e:
            logger.error(f"파드 상세 정보 가져오기 중 API 오류 발생: {e}")
            if e.status == 404:
                return {"error": f"파드를 찾을 수 없습니다: {namespace}/{name}"}
            raise
        except Exception as e:
            logger.error(f"파드 상세 정보 가져오기 중 오류 발생: {e}")
            raise


# 싱글톤 인스턴스 생성
try:
    kubernetes_api = KubernetesAPIService()
except Exception as e:
    logger.error(f"Kubernetes API 서비스 초기화 실패: {e}")
    kubernetes_api = None


@app.tool()
def get_cluster_info() -> dict:
    """
    Kubernetes 클러스터 정보를 가져옵니다.
    
    Returns:
        dict: 클러스터 정보를 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        cluster_info = kubernetes_api.get_cluster_info()
        return {
            "result": cluster_info.__dict__
        }
    except Exception as e:
        logger.error(f"클러스터 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"클러스터 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_nodes() -> dict:
    """
    Kubernetes 노드 목록을 가져옵니다.
    
    Returns:
        dict: 노드 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        nodes = kubernetes_api.get_nodes()
        return {
            "result": [node.__dict__ for node in nodes]
        }
    except Exception as e:
        logger.error(f"노드 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"노드 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_namespaces() -> dict:
    """
    Kubernetes 네임스페이스 목록을 가져옵니다.
    
    Returns:
        dict: 네임스페이스 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        namespaces = kubernetes_api.get_namespaces()
        return {
            "result": namespaces
        }
    except Exception as e:
        logger.error(f"네임스페이스 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"네임스페이스 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_pods(namespace: str = None, label_selector: str = None, field_selector: str = None) -> dict:
    """
    Kubernetes 파드 목록을 가져옵니다.
    
    Args:
        namespace: 네임스페이스 (None이면 모든 네임스페이스)
        label_selector: 레이블 셀렉터 (예: "app=nginx")
        field_selector: 필드 셀렉터 (예: "status.phase=Running")
        
    Returns:
        dict: 파드 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        pods = kubernetes_api.get_pods(namespace, label_selector, field_selector)
        return {
            "result": [pod.__dict__ for pod in pods]
        }
    except Exception as e:
        logger.error(f"파드 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"파드 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_pod_logs(name: str, namespace: str, container: str = None, tail_lines: int = 100, previous: bool = False) -> dict:
    """
    Kubernetes 파드 로그를 가져옵니다.
    
    Args:
        name: 파드 이름
        namespace: 네임스페이스
        container: 컨테이너 이름 (None이면 첫 번째 컨테이너)
        tail_lines: 가져올 로그 라인 수 (기본값: 100)
        previous: 이전 컨테이너의 로그 가져오기 여부 (기본값: False)
        
    Returns:
        dict: 파드 로그를 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        logs = kubernetes_api.get_pod_logs(name, namespace, container, tail_lines, previous)
        return {
            "result": logs
        }
    except Exception as e:
        logger.error(f"파드 로그 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"파드 로그 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_services(namespace: str = None, label_selector: str = None) -> dict:
    """
    Kubernetes 서비스 목록을 가져옵니다.
    
    Args:
        namespace: 네임스페이스 (None이면 모든 네임스페이스)
        label_selector: 레이블 셀렉터 (예: "app=nginx")
        
    Returns:
        dict: 서비스 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        services = kubernetes_api.get_services(namespace, label_selector)
        return {
            "result": [service.__dict__ for service in services]
        }
    except Exception as e:
        logger.error(f"서비스 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"서비스 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_deployments(namespace: str = None, label_selector: str = None) -> dict:
    """
    Kubernetes 디플로이먼트 목록을 가져옵니다.
    
    Args:
        namespace: 네임스페이스 (None이면 모든 네임스페이스)
        label_selector: 레이블 셀렉터 (예: "app=nginx")
        
    Returns:
        dict: 디플로이먼트 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        deployments = kubernetes_api.get_deployments(namespace, label_selector)
        return {
            "result": [deployment.__dict__ for deployment in deployments]
        }
    except Exception as e:
        logger.error(f"디플로이먼트 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"디플로이먼트 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_events(namespace: str = None, field_selector: str = None, sort_by: str = "lastTimestamp") -> dict:
    """
    Kubernetes 이벤트 목록을 가져옵니다.
    
    Args:
        namespace: 네임스페이스 (None이면 모든 네임스페이스)
        field_selector: 필드 셀렉터 (예: "involvedObject.name=nginx")
        sort_by: 정렬 기준 (lastTimestamp 또는 firstTimestamp)
        
    Returns:
        dict: 이벤트 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        events = kubernetes_api.get_events(namespace, field_selector, sort_by)
        return {
            "result": [event.__dict__ for event in events]
        }
    except Exception as e:
        logger.error(f"이벤트 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"이벤트 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def describe_pod(name: str, namespace: str) -> dict:
    """
    Kubernetes 파드 상세 정보를 가져옵니다.
    
    Args:
        name: 파드 이름
        namespace: 네임스페이스
        
    Returns:
        dict: 파드 상세 정보를 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        pod_info = kubernetes_api.describe_pod(name, namespace)
        return {
            "result": pod_info
        }
    except Exception as e:
        logger.error(f"파드 상세 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"파드 상세 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_pods_by_node(node_name: str) -> dict:
    """
    특정 노드에서 실행 중인 파드 목록을 가져옵니다.
    
    Args:
        node_name: 노드 이름
        
    Returns:
        dict: 파드 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        field_selector = f"spec.nodeName={node_name}"
        pods = kubernetes_api.get_pods(field_selector=field_selector)
        return {
            "result": [pod.__dict__ for pod in pods]
        }
    except Exception as e:
        logger.error(f"노드 파드 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"노드 파드 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_pods_by_service(service_name: str, namespace: str) -> dict:
    """
    특정 서비스에 연결된 파드 목록을 가져옵니다.
    
    Args:
        service_name: 서비스 이름
        namespace: 네임스페이스
        
    Returns:
        dict: 파드 목록을 포함한 딕셔너리
    """
    try:
        if not kubernetes_api:
            return {"error": "Kubernetes API 서비스가 초기화되지 않았습니다."}
        
        # 서비스 정보 가져오기
        services = kubernetes_api.get_services(namespace=namespace)
        service = None
        for svc in services:
            if svc.name == service_name:
                service = svc
                break
        
        if not service:
            return {"error": f"서비스를 찾을 수 없습니다: {namespace}/{service_name}"}
        
        # 서비스 셀렉터가 없는 경우
        if not service.selector:
            return {"result": []}
        
        # 셀렉터를 레이블 셀렉터 문자열로 변환
        label_selector = ",".join([f"{k}={v}" for k, v in service.selector.items()])
        
        # 셀렉터에 맞는 파드 가져오기
        pods = kubernetes_api.get_pods(namespace=namespace, label_selector=label_selector)
        return {
            "result": [pod.__dict__ for pod in pods]
        }
    except Exception as e:
        logger.error(f"서비스 파드 정보 가져오기 중 오류 발생: {str(e)}")
        return {"error": f"서비스 파드 정보 가져오기 중 오류 발생: {str(e)}"}


@app.tool()
def get_tool_info() -> dict:
    """
    Kubernetes API 도구 정보를 반환합니다.
    
    Returns:
        dict: 도구 정보를 포함한 딕셔너리
    """
    try:
        return {
            "result": {
                "name": "Kubernetes API Tool",
                "description": "Kubernetes API를 통해 클러스터 상황, pod 현황, 로그 조회, 이벤트 조회 등 다양한 observability 기능을 제공하는 도구",
                "auth_status": "인증됨" if kubernetes_api else "인증되지 않음",
                "tools": [
                    {"name": "get_cluster_info", "description": "Kubernetes 클러스터 정보를 가져옵니다"},
                    {"name": "get_nodes", "description": "Kubernetes 노드 목록을 가져옵니다"},
                    {"name": "get_namespaces", "description": "Kubernetes 네임스페이스 목록을 가져옵니다"},
                    {"name": "get_pods", "description": "Kubernetes 파드 목록을 가져옵니다"},
                    {"name": "get_pod_logs", "description": "Kubernetes 파드 로그를 가져옵니다"},
                    {"name": "get_services", "description": "Kubernetes 서비스 목록을 가져옵니다"},
                    {"name": "get_deployments", "description": "Kubernetes 디플로이먼트 목록을 가져옵니다"},
                    {"name": "get_events", "description": "Kubernetes 이벤트 목록을 가져옵니다"},
                    {"name": "describe_pod", "description": "Kubernetes 파드 상세 정보를 가져옵니다"},
                    {"name": "get_pods_by_node", "description": "특정 노드에서 실행 중인 파드 목록을 가져옵니다"},
                    {"name": "get_pods_by_service", "description": "특정 서비스에 연결된 파드 목록을 가져옵니다"}
                ],
                "usage_examples": [
                    {"command": "get_cluster_info()", "description": "클러스터 정보 가져오기"},
                    {"command": "get_pods(namespace='default')", "description": "default 네임스페이스의 파드 목록 가져오기"},
                    {"command": "get_pod_logs(name='nginx-pod', namespace='default')", "description": "파드 로그 가져오기"},
                    {"command": "get_events(namespace='kube-system')", "description": "kube-system 네임스페이스의 이벤트 가져오기"},
                    {"command": "describe_pod(name='nginx-pod', namespace='default')", "description": "파드 상세 정보 가져오기"}
                ],
                "authentication": {
                    "required": True,
                    "method": "kubeconfig",
                    "environment_variables": [
                        "KUBECONFIG - kubeconfig 파일 경로 (기본값: ~/.kube/config)"
                    ]
                }
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
        logger.error("kubernetes_tool.py 스크립트 최상위에서 처리되지 않은 예외 발생", exc_info=True)
        raise