from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run("knowledge_gateway.app:create_app", host="0.0.0.0", port=8080, factory=True)
