import time
from collections import defaultdict

_user_requests = defaultdict(list)

def check_rate_limit(user_id: int, action: str = None, limit: int = 5, period: int = 60) -> bool:
    key = f"{user_id}_{action}" if action else str(user_id)
    current = time.time()
    
    if key in _user_requests:
        _user_requests[key] = [t for t in _user_requests[key] if current - t < period]
        if len(_user_requests[key]) >= limit:
            return False
        _user_requests[key].append(current)
    else:
        _user_requests[key] = [current]
    
    return True
