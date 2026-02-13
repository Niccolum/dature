class TablePathFinder:
    def __init__(self, content: str):
        self.lines = content.splitlines()

    def find_line(self, target_path: list[str]) -> int:
        target_key = target_path[-1]
        target_parents = target_path[:-1]
        current_section = []

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                continue

            # Working with sections [section] or [parent.child]
            if stripped.startswith("[") and "]" in stripped:
                section_name = stripped.strip("[] ")
                current_section = section_name.split(".")
                continue

            # Working with keys key = value
            sep = "=" if "=" in stripped else ":"
            if sep in stripped:
                key = stripped.partition(sep)[0].strip().strip("\"'")
                if key == target_key and current_section == target_parents:
                    return i
        return -1
