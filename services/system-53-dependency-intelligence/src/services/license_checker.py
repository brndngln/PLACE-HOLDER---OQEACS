from __future__ import annotations

from src.models import DependencyTree, LicenseInfo


class LicenseChecker:
    LICENSE_MAP: dict[str, str] = {
        "fastapi": "MIT",
        "django": "BSD-3-Clause",
        "gpl-lib": "GPL-3.0",
    }

    def check_licenses(self, tree: DependencyTree) -> list[LicenseInfo]:
        infos: list[LicenseInfo] = []
        has_gpl = False
        for node in tree.nodes:
            lic = self.LICENSE_MAP.get(node.name.lower(), "UNKNOWN")
            if lic.startswith("GPL"):
                has_gpl = True
            infos.append(LicenseInfo(package=node.name, license=lic, compatible=True, notes=""))

        if has_gpl:
            for info in infos:
                if info.license in {"MIT", "BSD-3-Clause", "Apache-2.0"}:
                    info.compatible = False
                    info.notes = "Potential copyleft conflict with GPL dependencies"
        return infos
