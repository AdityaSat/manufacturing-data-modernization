"""Commands work from a fresh clone, without an editable install."""
import argparse
import functools
import http.server
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
parser = argparse.ArgumentParser(description="Manufacturing Data Modernization & AI Business Case")
sub = parser.add_subparsers(dest="command", required=True)
build = sub.add_parser("build", help="Validate data, load SQL, train and export dashboard data")
build.add_argument("--download", action="store_true", help="Refresh source CSV from UCI")
serve = sub.add_parser("dashboard", help="Serve the prebuilt dashboard locally")
serve.add_argument("--port", type=int, default=8000)
args = parser.parse_args()
if args.command == "build":
    from manufacturing.pipeline import run
    run(download_data=args.download)
else:
    if not (ROOT / "dashboard/data.json").exists():
        parser.error("Run python run.py build first")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "dashboard"))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Dashboard: http://localhost:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
