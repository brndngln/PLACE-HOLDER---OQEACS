from __future__ import annotations

import hashlib

from src.models import DependencyTree, SBOMDocument


class SBOMGenerator:
    def generate_sbom(self, tree: DependencyTree) -> SBOMDocument:
        components: list[dict] = []
        for node in tree.nodes:
            purl_type = "pypi" if node.ecosystem == "pypi" else node.ecosystem
            bom_ref = f"pkg:{purl_type}/{node.name}@{node.version}"
            digest = hashlib.sha256(f"{node.name}:{node.version}".encode()).hexdigest()
            components.append(
                {
                    "type": "library",
                    "name": node.name,
                    "version": node.version,
                    "bom-ref": bom_ref,
                    "purl": bom_ref,
                    "hashes": [{"alg": "SHA-256", "content": digest}],
                }
            )
        return SBOMDocument(components=components)
