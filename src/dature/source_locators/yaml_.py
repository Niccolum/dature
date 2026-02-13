class YamlPathFinder:
    def __init__(self, content: str):
        self.lines = content.splitlines()

    def find_line(self, target_path: list[str]) -> int:
        stack: list[dict[str, str | int]] = []
        for i, line in enumerate(self.lines, 1):
            stripped = line.lstrip()
            if not stripped or stripped.startswith(("#", "-")):
                continue

            indent = len(line) - len(stripped)
            # Separate by the first colon
            key_part, sep, _ = stripped.partition(":")
            if not sep:
                continue

            key = key_part.strip().strip("\"'")

            while stack and int(stack[-1]["indent"]) >= indent:
                stack.pop()

            stack.append({"key": key, "indent": indent})
            if [item["key"] for item in stack] == target_path:
                return i
        return -1
