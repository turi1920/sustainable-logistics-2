import os
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")

class ApiClient:
    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url.rstrip("/")

    def _headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username_or_email": username_or_email, "password": password},
            timeout=10
        )
        if resp.status_code != 200:
            error_msg = resp.json().get("detail", "Login failed")
            raise Exception(error_msg)
        return resp.json()

    def get_me(self, token: str) -> Dict[str, Any]:
        resp = requests.get(
            f"{self.base_url}/api/auth/me",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to fetch user profile"))
        return resp.json()

    def list_organizations(self, token: str) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{self.base_url}/api/organizations",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to fetch organizations"))
        return resp.json()

    def list_returns(self, token: str, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if status and status != "ALL":
            params["status"] = status
        if search:
            params["search"] = search
        resp = requests.get(
            f"{self.base_url}/api/returns",
            headers=self._headers(token),
            params=params,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to list returns"))
        return resp.json()

    def get_return(self, token: str, return_id: str) -> Dict[str, Any]:
        resp = requests.get(
            f"{self.base_url}/api/returns/{return_id}",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to get return {return_id}"))
        return resp.json()

    def get_return_journey(self, token: str, return_id: str) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{self.base_url}/api/returns/{return_id}/journey",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to get journey for {return_id}"))
        return resp.json()

    def create_return(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code not in (200, 201):
            raise Exception(resp.json().get("detail", "Failed to create return"))
        return resp.json()

    def receive_return(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/receive",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to receive return {return_id}"))
        return resp.json()

    def inspect_return(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/inspect",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to inspect return {return_id}"))
        return resp.json()

    def decide_return(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/decide",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to record retailer decision for {return_id}"))
        return resp.json()

    def process_return(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/process",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to complete processing for {return_id}"))
        return resp.json()

    def qc_return(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/qc",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to complete QC for {return_id}"))
        return resp.json()

    def restock_return(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/restock",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to restock return {return_id}"))
        return resp.json()

api_client = ApiClient()
