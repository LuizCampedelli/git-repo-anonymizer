import os
import re
import shutil
from pathlib import Path

# Common regex patterns for sensitive data
PATTERNS = {
    "IP_ADDRESS": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    "BEARER_TOKEN": r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*",
    "GENERIC_SECRET": r"(?i)(password|passwd|secret|token|api_key|private_key|passwd|pwd)\s*[:=]\s*['\"]([^'\"]+)['\"]",
    "AWS_KEY": r"\b(AKIA|ASCA|ASIA)[A-Z0-9]{16}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
}

# Directories/Files to completely skip (includes "anonymizer" output folder)
IGNORE_LIST = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache", ".DS_Store", "anonymizer"}

class CodeAnonymizer:
    def __init__(self, src_dir, dst_dir):
        self.src_dir = Path(src_dir)
        self.dst_dir = Path(dst_dir)
        self.mappings = {}
        self.counters = {key: 1 for key in PATTERNS.keys()}

    def get_placeholder(self, pattern_type, original_value):
        if pattern_type == "GENERIC_SECRET":
            pass

        for placeholder, val in self.mappings.items():
            if val == original_value:
                return placeholder

        placeholder = f"[MASKED_{pattern_type}_{self.counters[pattern_type]}]"
        self.mappings[placeholder] = original_value
        self.counters[pattern_type] += 1
        return placeholder

    def anonymize_text(self, text):
        anonymized = text

        for name, pattern in PATTERNS.items():
            if name == "GENERIC_SECRET":
                continue

            matches = set(re.findall(pattern, anonymized))
            for match in matches:
                placeholder = self.get_placeholder(name, match)
                anonymized = anonymized.replace(match, placeholder)

        def secret_replacer(match):
            full_match = match.group(0)
            secret_val = match.group(2)
            placeholder = self.get_placeholder("GENERIC_SECRET", secret_val)
            return full_match.replace(secret_val, placeholder)

        anonymized = re.sub(PATTERNS["GENERIC_SECRET"], secret_replacer, anonymized)
        return anonymized

    def process_project(self):
        # Instead of deleting the mount point, clear its contents
        if self.dst_dir.exists():
            for item in self.dst_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        else:
            self.dst_dir.mkdir(parents=True, exist_ok=True)

        for root, dirs, files in os.walk(self.src_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

            rel_path = Path(root).relative_to(self.src_dir)
            target_root = self.dst_dir / rel_path
            target_root.mkdir(parents=True, exist_ok=True)

            for file in files:
                if file in IGNORE_LIST:
                    continue

                src_file_path = Path(root) / file
                dst_file_path = target_root / file

                try:
                    content = src_file_path.read_text(encoding="utf-8", errors="replace")
                    clean_content = self.anonymize_text(content)
                    dst_file_path.write_text(clean_content, encoding="utf-8")
                except Exception:
                    shutil.copy2(src_file_path, dst_file_path)

    def generate_report(self, report_path):
        md_content = [
            "# Data Anonymization Report\n",
            "This document maps the placeholders injected into the cloned codebase back to their original configuration values. **Do not share this file with LLMs.**\n",
            "| Placeholder | Original Sensitive Value |",
            "| :--- | :--- |"
        ]

        for placeholder, original in self.mappings.items():
            md_content.append(f"| `{placeholder}` | `{original}` |")

        Path(report_path).write_text("\n".join(md_content), encoding="utf-8")

if __name__ == "__main__":
    SOURCE = "/app/src"
    DESTINATION = "/app/sanitized"
    REPORT = "/app/sanitized/anonymization_report.md"

    print("[*] Initializing repository sweep...")
    anonymizer = CodeAnonymizer(SOURCE, DESTINATION)
    anonymizer.process_project()
    anonymizer.generate_report(REPORT)
    print(f"[+] Success! Sanitized project and report written to {DESTINATION}")
