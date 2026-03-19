"""Entry point — python -m denai"""

import uvicorn

from .config import HOST, PORT


def main():
    uvicorn.run(
        "denai.app:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
