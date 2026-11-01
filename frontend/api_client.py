import os
from typing import Any, Dict, List, Optional

import requests

API_BASE = (
    os.getenv("BACKEND_API_URL")
    or os.getenv("API_BASE_URL")
    or "http://127.0.0.1:8000"
).rstrip("/")

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

    def generate_return_id(self, token: str, prefix: str = "RET") -> Dict[str, Any]:
        resp = requests.get(
            f"{self.base_url}/api/returns/generate-id",
            headers=self._headers(token),
            params={"prefix": prefix},
            timeout=10,
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to generate return ID"))
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

    # User Management APIs
    def list_users(self, token: str) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{self.base_url}/api/users",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to list users"))
        return resp.json()

    def create_user(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/users",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code not in (200, 201):
            raise Exception(resp.json().get("detail", "Failed to create user"))
        return resp.json()

    def delete_user(self, token: str, user_id: int) -> Dict[str, Any]:
        resp = requests.delete(
            f"{self.base_url}/api/users/{user_id}",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to delete user {user_id}"))
        return resp.json()

    def toggle_user_active(self, token: str, user_id: int) -> Dict[str, Any]:
        resp = requests.patch(
            f"{self.base_url}/api/users/{user_id}/toggle-active",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to toggle user status for {user_id}"))
        return resp.json()

    # Pickup Partner APIs
    def list_pickup_partners(self, token: str) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{self.base_url}/api/pickup-partners",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to list pickup partners"))
        return resp.json()

    def create_pickup_partner(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/pickup-partners",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code not in (200, 201):
            raise Exception(resp.json().get("detail", "Failed to create pickup partner"))
        return resp.json()

    def delete_pickup_partner(self, token: str, partner_id: int) -> Dict[str, Any]:
        resp = requests.delete(
            f"{self.base_url}/api/pickup-partners/{partner_id}",
            headers=self._headers(token),
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to delete pickup partner {partner_id}"))
        return resp.json()

    def assign_pickup_partner(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/assign-pickup",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to assign pickup partner for {return_id}"))
        return resp.json()

    def confirm_pickup_collection(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/confirm-pickup",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to confirm collection for {return_id}"))
        return resp.json()

    def deliver_pickup_to_warehouse(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/deliver-warehouse",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to deliver shipment {return_id} to warehouse"))
        return resp.json()

    def fail_pickup_collection(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/fail-pickup",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to report pickup failure for {return_id}"))
        return resp.json()

    def reschedule_pickup(self, token: str, return_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/reschedule-pickup",
            headers=self._headers(token),
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to reschedule pickup for {return_id}"))
        return resp.json()

    def list_marketplace_returns(self, token: str) -> List[Dict[str, Any]]:
        resp = requests.get(
            f"{self.base_url}/api/returns/marketplace",
            headers=self._headers(token),
            timeout=10,
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to list marketplace returns"))
        return resp.json()

    def accept_marketplace_task(self, token: str, return_id: str) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/accept",
            headers=self._headers(token),
            timeout=10,
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to accept task {return_id}"))
        return resp.json()

    def reject_marketplace_task(self, token: str, return_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/reject",
            headers=self._headers(token),
            json={"reason": reason} if reason else {},
            timeout=10,
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to reject task {return_id}"))
        return resp.json()

    def release_driver_task(self, token: str, return_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/api/returns/{return_id}/release",
            headers=self._headers(token),
            json={"reason": reason} if reason else {},
            timeout=10,
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", f"Failed to release task {return_id}"))
        return resp.json()

    def get_sustainability_summary(self, token: str, organization_id: Optional[int] = None) -> Dict[str, Any]:
        params = {}
        if organization_id:
            params["organization_id"] = organization_id
        resp = requests.get(
            f"{self.base_url}/api/sustainability/summary",
            headers=self._headers(token),
            params=params,
            timeout=10
        )
        if resp.status_code != 200:
            raise Exception(resp.json().get("detail", "Failed to fetch sustainability summary"))
        return resp.json()

api_client = ApiClient()
