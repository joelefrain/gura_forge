import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from modules.downloader.records_downloader import SeismicDownloader

orchestrator = SeismicDownloader()

try:
    # Procesar eventos recientes del catálogo IGP
    result = orchestrator.process_recent_events(
        catalog="igp",
        num_events=5310,
        max_workers=80,
    )

    print("\n" + "=" * 60)
    print("RESULTADO DEL PIPELINE ETL")
    print("=" * 60)
    print(f"Catálogo: {result.get('catalog')}")
    print(f"Estado: {result.get('status')}")
    print(
        f"Eventos procesados: {result.get('processed_events')}/{result.get('total_events')}"
    )
    print(f"Eventos exitosos: {result.get('successful_events')}")
    print(f"Eventos fallidos: {result.get('failed_events')}")

    if result.get("errors"):
        print("\nErrores:")
        for error in result["errors"][:5]:
            print(f"  - {error}")

except Exception as e:
    print(f"Error en ejecución: {e}")

finally:
    orchestrator.close()
