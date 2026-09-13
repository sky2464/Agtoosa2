#!/usr/bin/env python3
"""Build and package the Agtoosa VS Code & Cursor extension into a production .vsix bundle.

Follows the Open Packaging Conventions (OPC) / VS Code VSIX specification.
Zero dependencies — runs purely on Python standard library.
"""

from __future__ import annotations
import json
import re
import sys
import zipfile
from pathlib import Path


def build_vsix(repo_root: Path, output_dir: Path | None = None) -> Path:
    ext_dir = repo_root / "extension"
    pkg_json_path = ext_dir / "package.json"

    if not pkg_json_path.exists():
        raise FileNotFoundError(f"package.json not found at {pkg_json_path}")

    with open(pkg_json_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)

    name = pkg_data.get("name", "agtoosa-vscode")
    version = pkg_data.get("version", "0.5.0")
    publisher = pkg_data.get("publisher", "agtoosa")
    display_name = pkg_data.get("displayName", "Agtoosa")
    description = pkg_data.get("description", "")
    keywords = ",".join(pkg_data.get("keywords", []))
    categories = ",".join(pkg_data.get("categories", []))
    engine = pkg_data.get("engines", {}).get("vscode", "^1.85.0")

    dest_dir = output_dir or (repo_root / "dist")
    dest_dir.mkdir(parents=True, exist_ok=True)
    vsix_filename = f"{name}-{version}.vsix"
    vsix_path = dest_dir / vsix_filename

    # 1. Generate extension.vsixmanifest
    escaped_display_name = display_name.replace("&", "&amp;")
    escaped_description = description.replace("&", "&amp;")

    vsix_manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
\t<Metadata>
\t\t<Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{publisher}" />
\t\t<DisplayName>{escaped_display_name}</DisplayName>
\t\t<Description xml:space="preserve">{escaped_description}</Description>
\t\t<Tags>{keywords}</Tags>
\t\t<Categories>{categories}</Categories>
\t\t<GalleryFlags>Public</GalleryFlags>
\t\t<Properties>
\t\t\t<Property Id="Microsoft.VisualStudio.Code.Engine" Value="{engine}" />
\t\t\t<Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
\t\t\t<Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
\t\t\t<Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
\t\t\t<Property Id="Microsoft.VisualStudio.Code.ExecutesCode" Value="true" />
\t\t\t<Property Id="Microsoft.VisualStudio.Services.Links.Source" Value="https://github.com/sky2464/Agtoosa2.git" />
\t\t\t<Property Id="Microsoft.VisualStudio.Services.Links.Getstarted" Value="https://github.com/sky2464/Agtoosa2.git" />
\t\t\t<Property Id="Microsoft.VisualStudio.Services.Links.GitHub" Value="https://github.com/sky2464/Agtoosa2.git" />
\t\t\t<Property Id="Microsoft.VisualStudio.Services.Links.Support" Value="https://github.com/sky2464/Agtoosa2/issues" />
\t\t\t<Property Id="Microsoft.VisualStudio.Services.Links.Learn" Value="https://github.com/sky2464/Agtoosa2#readme" />
\t\t\t<Property Id="Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown" Value="true" />
\t\t\t<Property Id="Microsoft.VisualStudio.Services.Content.Pricing" Value="Free"/>
\t\t</Properties>
\t</Metadata>
\t<Installation>
\t\t<InstallationTarget Id="Microsoft.VisualStudio.Code"/>
\t</Installation>
\t<Dependencies/>
\t<Assets>
\t\t<Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
\t\t<Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />
\t</Assets>
</PackageManifest>
"""

    # 2. Generate [Content_Types].xml
    content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
\t<Default Extension=".js" ContentType="application/javascript"/>
\t<Default Extension=".json" ContentType="application/json"/>
\t<Default Extension=".md" ContentType="text/markdown"/>
\t<Default Extension=".svg" ContentType="image/svg+xml"/>
\t<Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
"""

    # 3. Read .vscodeignore patterns
    ignore_patterns = [
        r"^\.vsix$",
        r"\.vsix$",
        r"node_modules",
        r"\.git",
        r"\.DS_Store",
        r"\.vscode"
    ]
    ignore_file = ext_dir / ".vscodeignore"
    if ignore_file.exists():
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                clean = line.replace(".", r"\.").replace("*", ".*")
                ignore_patterns.append(clean)

    ignore_re = re.compile("|".join(ignore_patterns))

    # 4. Pack into zip archive
    with zipfile.ZipFile(vsix_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("extension.vsixmanifest", vsix_manifest.strip())
        z.writestr("[Content_Types].xml", content_types.strip())

        for file_path in sorted(ext_dir.rglob("*")):
            if file_path.is_file():
                rel = file_path.relative_to(ext_dir).as_posix()
                if ignore_re.search(rel):
                    continue
                z.write(file_path, f"extension/{rel}")

    # Also update extension copy
    ext_copy = ext_dir / vsix_filename
    with open(vsix_path, "rb") as src, open(ext_copy, "wb") as dst:
        dst.write(src.read())

    print(f"📦 Successfully packaged VS Code / Cursor extension:")
    print(f"   • VSIX file: {vsix_path}")
    print(f"   • Version:   {version}")
    print(f"   • Size:      {vsix_path.stat().st_size / 1024:.1f} KB")

    return vsix_path


def main():
    repo_root = Path(__file__).resolve().parent.parent
    try:
        build_vsix(repo_root)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to package extension: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
