"""Entry point — python -m denai"""

import uvicorn


def main():
    # Processar --profile antes de importar config (DATA_DIR dinâmico)
    import sys

    profile = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--profile" and i < len(sys.argv):
            profile = sys.argv[i + 1]
        elif arg.startswith("--profile="):
            profile = arg.split("=", 1)[1]

    if profile:
        from .profile_manager import set_active_profile

        try:
            set_active_profile(profile)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)

    from .config import HOST, PORT

    uvicorn.run(
        "denai.app:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
