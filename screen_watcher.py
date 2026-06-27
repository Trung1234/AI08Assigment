#!/usr/bin/env python
"""Screen Watcher — CLI entry point.

Usage:
  python screen_watcher.py run --config config.yaml
  python screen_watcher.py test-capture --config config.yaml
  python screen_watcher.py test-ocr --config config.yaml
  python screen_watcher.py test-rule --config config.yaml
  python screen_watcher.py test-email --config config.yaml
"""
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:
    typer = None

from screen_watcher.models import EmailConfig, OwnerGroup, Rule
from screen_watcher.notification_service import NotificationService
from screen_watcher.rule_engine import RuleEngine
from screen_watcher.state_store import StateStore

logger = logging.getLogger(__name__)

# CLI app
if typer:
    app = typer.Typer()
else:
    # Fallback: simple argparse-like interface nếu không có typer
    class SimpleApp:
        def __init__(self):
            self.commands = {}

        def command(self, name):
            def decorator(func):
                self.commands[name] = func
                return func

            return decorator

        def run(self, argv):
            if len(argv) < 1:
                self._print_help()
                sys.exit(1)
            cmd = argv[0]
            if cmd not in self.commands:
                print(f"Unknown command: {cmd}")
                self._print_help()
                sys.exit(1)
            self.commands[cmd](argv[1:])

        def _print_help(self):
            print("Usage: python screen_watcher.py <command> --config <path>")
            print("Commands:")
            for name in self.commands:
                print(f"  {name}")

    app = SimpleApp()


# ─── Commands ──────────────────────────────────────────────────────


@app.command()
def run(config: str = typer.Option(..., help="Path to config.yaml")):
    """Run the full Screen Watcher workflow."""
    print(f"[INFO] Starting Screen Watcher with config: {config}")
    print(
        "[TODO] Full workflow not yet implemented in Phase 1. "
        "Phase 1 scope: Rule Engine + Email Notification only. "
        "Missing: Screen Capture + OCR modules."
    )
    print(
        "[TODO] For now, use test-* commands to verify each component independently."
    )


@app.command()
def test_capture(config: str = typer.Option(..., help="Path to config.yaml")):
    """Test screen capture functionality."""
    print(f"[INFO] test-capture: {config}")
    print(
        "[TODO] Screen Capture module not yet implemented in Phase 1. "
        "Scope: Rule Engine + Email Notification only."
    )
    print("Expected: screenshot saved to data/screenshots/")


@app.command()
def test_ocr(config: str = typer.Option(..., help="Path to config.yaml")):
    """Test OCR text extraction."""
    print(f"[INFO] test-ocr: {config}")
    print(
        "[TODO] OCR Service module not yet implemented in Phase 1. "
        "Scope: Rule Engine + Email Notification only."
    )
    print("Expected: OCR text saved to data/ocr/")


@app.command()
def test_rule(config: str = typer.Option(..., help="Path to config.yaml")):
    """Test rule matching with sample text."""
    print(f"[INFO] test-rule with config: {config}")

    # ← Demonstrasi use RuleEngine (đã implement)
    rules = [
        Rule(
            id="demo-error",
            name="Error Detected",
            type="regex",
            severity="high",
            owner_group="ops",
            cooldown_minutes=15,
            pattern=r"(ERROR|FAILED)",
            ignore_case=True,
        ),
        Rule(
            id="demo-ok",
            name="Service Running",
            type="not_contains",
            severity="low",
            owner_group="ops",
            cooldown_minutes=0,
            keywords=["Service Down"],
        ),
    ]

    engine = RuleEngine(rules)

    # Test cases
    test_texts = [
        ("System error at 10:05", "should match error rule"),
        ("Service is running OK", "should match service rule"),
        ("All good", "should not match any rule"),
    ]

    for text, description in test_texts:
        matches = engine.evaluate(text)
        print(f"\nText: {text}")
        print(f"Description: {description}")
        if matches:
            for m in matches:
                print(f"  [OK] Matched: {m.rule_name} (severity={m.severity.value})")
        else:
            print("  [NO] No match")


@app.command()
def test_email(config: str = typer.Option(..., help="Path to config.yaml")):
    """Test email sending (requires SMTP config and mock)."""
    print(f"[INFO] test-email with config: {config}")
    print(
        "[INFO] Email Service supports SMTP, but actual send requires config. "
        "For unit testing, see: python -m unittest tests.test_email_service -v"
    )
    print(
        "[TODO] Full test-email command needs config loader + SMTP credentials from env."
    )


# ─── Main ──────────────────────────────────────────────────────────


def main():
    if typer:
        # Typer mode
        app()
    else:
        # Fallback mode (parse sys.argv)
        if len(sys.argv) < 2:
            print("Usage: python screen_watcher.py <command> --config <path>")
            print("Commands: run, test-capture, test-ocr, test-rule, test-email")
            sys.exit(1)
        cmd = sys.argv[1]
        argv = sys.argv[2:]
        if hasattr(app, "run"):
            # SimpleApp mode
            app.run([cmd] + argv)
        else:
            # Typer mode
            app()


if __name__ == "__main__":
    main()
