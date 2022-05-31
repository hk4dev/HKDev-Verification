from typing import Dict, Any, Optional


class VerificationResponse:
    def __init__(self, payload: Dict[str, Any]):
        self.result = payload['result']
        self.time = self._get_int(payload.get('responseTime'))

    @staticmethod
    def _get_int(data: Optional[Any]) -> Optional[int]:
        if data is not None:
            return int(data)
        return
