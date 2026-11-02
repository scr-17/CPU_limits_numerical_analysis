"""Punto de entrada del simulador térmico."""

if __package__:
    from .interfaz import main
else:
    import sys
    from pathlib import Path

    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.interfaz import main


if __name__ == "__main__":
    main()
