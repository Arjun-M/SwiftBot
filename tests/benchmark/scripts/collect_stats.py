import argparse
import json
import sys
from importlib import metadata
from pathlib import Path


def path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob('*') if item.is_file())


def distribution_size(dist):
    total = 0
    files = []
    for file in dist.files or []:
        path = dist.locate_file(file)
        if path.exists() and path.is_file():
            total += path.stat().st_size
            files.append(str(file))
    return total, len(files)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--distribution', required=True)
    parser.add_argument('--venv', required=True, type=Path)
    parser.add_argument('--framework-module', required=True)
    args = parser.parse_args()

    dist = metadata.distribution(args.distribution)
    package_size, file_count = distribution_size(dist)
    site_packages = args.venv / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    env_size = path_size(args.venv)
    site_packages_size = path_size(site_packages)
    direct_requires = []
    for req in dist.requires or []:
        if ';' not in req or 'extra ==' not in req:
            direct_requires.append(req)

    result = {
        'distribution': args.distribution,
        'version': dist.version,
        'python': sys.version.split()[0],
        'module': args.framework_module,
        'package_size_bytes': package_size,
        'package_size_kib': package_size / 1024,
        'package_file_count': file_count,
        'venv_size_bytes': env_size,
        'venv_size_mib': env_size / (1024 * 1024),
        'site_packages_size_bytes': site_packages_size,
        'site_packages_size_mib': site_packages_size / (1024 * 1024),
        'direct_requires': direct_requires,
        'all_requires_count': len(dist.requires or []),
        'metadata_summary': dist.metadata.get('Summary'),
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
